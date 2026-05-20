/**
 * TypeScript / Vue AST Analyzer for Context Builder Agent.
 * Uses TypeScript Compiler API to extract structure.
 *
 * Usage: node analyze.mjs <project_path> [file1.ts file2.ts ...]
 * Output: JSON on stdout
 */

import { readFileSync, readdirSync, statSync, existsSync } from 'fs';
import { join, relative, extname, dirname } from 'path';
import { fileURLToPath } from 'url';
import ts from 'typescript';

const projectPath = process.argv[2];
if (!projectPath) {
    console.error('Usage: node analyze.mjs <project_path> [files...]');
    process.exit(1);
}

const specificFiles = process.argv.slice(3);

// Find tsconfig.json
const tsconfigPath = join(projectPath, 'tsconfig.json');

// Find TS/Vue files
let files;
if (specificFiles.length > 0) {
    files = specificFiles.filter(f => {
        const ext = extname(f);
        return ['.ts', '.tsx', '.vue', '.mjs', '.js', '.jsx'].includes(ext);
    });
} else {
    files = findTsFiles(projectPath);
}

const result = { files: [], errors: [] };

if (files.length === 0) {
    console.log(JSON.stringify(result));
    process.exit(0);
}

// Read files standalone — programmatic mode can lose class members
// when type resolution fails. Standalone parsing always gives the full AST.

for (const file of files) {
    try {
        // Always use standalone parsing — program.getSourceFile() can return
        // ASTs with incomplete members when type resolution fails.
        const code = readFileSync(file, 'utf-8');
        const sf = ts.createSourceFile(file, code, ts.ScriptTarget.Latest, true);
        const fileInfo = extractFile(sf, file, projectPath);
        result.files.push(fileInfo);
    } catch (e) {
        result.errors.push({
            file: relative(projectPath, file).replace(/\\/g, '/'),
            message: e.message
        });
    }
}

console.log(JSON.stringify(result));

// ── Extractors ──────────────────────────────────────────────

function extractFile(sourceFile, filePath, basePath) {
    const relPath = relative(basePath, filePath).replace(/\\/g, '/');
    const info = {
        path: relPath,
        module: null,
        imports: [],
        classes: [],
        functions: []
    };

    // Extract imports
    sourceFile.forEachChild(node => {
        if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) {
            info.imports.push(node.moduleSpecifier.text);
        } else if (ts.isImportEqualsDeclaration(node) && ts.isExternalModuleReference(node.moduleReference)) {
            if (ts.isStringLiteral(node.moduleReference.expression)) {
                info.imports.push(node.moduleReference.expression.text);
            }
        } else if (ts.isExportDeclaration(node) && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) {
            info.imports.push(node.moduleSpecifier.text);
        }
    });

    // Extract require() calls
    const text = sourceFile.getFullText();
    const requireRe = /require\s*\(\s*['"]([^'"]+)['"]\s*\)/g;
    let m;
    while ((m = requireRe.exec(text)) !== null) {
        if (!info.imports.includes(m[1])) {
            info.imports.push(m[1]);
        }
    }

    // Walk the AST for classes, interfaces, functions
    function walk(node) {
        if (ts.isClassDeclaration(node) && node.name) {
            info.classes.push(extractClass(node, sourceFile));
        }
        if (ts.isInterfaceDeclaration(node) && node.name) {
            info.classes.push(extractInterface(node));
        }
        if (ts.isFunctionDeclaration(node) && node.name) {
            // Only top-level functions (not inside classes)
            if (node.parent === sourceFile || ts.isSourceFile(node.parent) || ts.isModuleBlock(node.parent)) {
                info.functions.push(extractFunction(node));
            }
        }
        ts.forEachChild(node, walk);
    }
    walk(sourceFile);

    return info;
}

function extractClass(node, sourceFile) {
    const cls = {
        name: node.name.text,
        type: 'class',
        extends: [],
        implements: [],
        decorators: [],
        methods: [],
        constructors: [],
        properties: [],
        loc: countLines(node, sourceFile)
    };

    // Decorators
    if (node.decorators) {
        for (const d of node.decorators) {
            cls.decorators.push(getDecoratorName(d));
        }
    }

    // Heritage
    if (node.heritageClauses) {
        for (const clause of node.heritageClauses) {
            for (const type of clause.types) {
                const name = type.expression.text;
                if (clause.token === ts.SyntaxKind.ExtendsKeyword) {
                    cls.extends.push(name);
                } else if (clause.token === ts.SyntaxKind.ImplementsKeyword) {
                    cls.implements.push(name);
                }
            }
        }
    }

    // Members
    for (const member of node.members) {
        if (ts.isMethodDeclaration(member) && member.name) {
            cls.methods.push(extractMethod(member));
        } else if (ts.isConstructorDeclaration(member)) {
            cls.constructors.push({
                parameters: extractParameters(member.parameters),
                modifiers: getModifiers(member)
            });
        } else if (ts.isPropertyDeclaration(member) && member.name) {
            cls.properties.push(extractProperty(member));
        } else if (ts.isGetAccessorDeclaration(member) && member.name) {
            cls.properties.push({
                name: `get ${getPropertyName(member.name)}`,
                type: member.type ? member.type.getText() : null,
                modifiers: getModifiers(member)
            });
        } else if (ts.isSetAccessorDeclaration(member) && member.name) {
            cls.properties.push({
                name: `set ${getPropertyName(member.name)}`,
                type: member.type ? member.type.getText() : null,
                modifiers: getModifiers(member)
            });
        }
    }

    return cls;
}

function extractInterface(node) {
    const iface = {
        name: node.name.text,
        type: 'interface',
        extends: [],
        implements: [],
        decorators: [],
        methods: [],
        constructors: [],
        properties: [],
        loc: 0
    };

    if (node.heritageClauses) {
        for (const clause of node.heritageClauses) {
            for (const type of clause.types) {
                iface.extends.push(type.expression.text);
            }
        }
    }

    for (const member of node.members) {
        if (ts.isMethodSignature(member) && member.name) {
            iface.methods.push({
                name: getPropertyName(member.name),
                return_type: member.type ? member.type.getText() : null,
                parameters: extractParameters(member.parameters),
                modifiers: [],
                attributes: [],
                loc: 0
            });
        } else if (ts.isPropertySignature(member) && member.name) {
            iface.properties.push({
                name: getPropertyName(member.name),
                type: member.type ? member.type.getText() : null,
                modifiers: [],
                attributes: []
            });
        }
    }

    return iface;
}

function extractMethod(node) {
    return {
        name: getPropertyName(node.name),
        return_type: node.type ? node.type.getText() : null,
        parameters: extractParameters(node.parameters),
        modifiers: getModifiers(node),
        attributes: [],
        loc: 0
    };
}

function extractProperty(node) {
    const decorators = [];
    if (node.decorators) {
        for (const d of node.decorators) {
            decorators.push(getDecoratorName(d));
        }
    }
    return {
        name: getPropertyName(node.name),
        type: node.type ? node.type.getText() : null,
        modifiers: getModifiers(node),
        attributes: decorators
    };
}

function extractFunction(node) {
    return {
        name: node.name.text,
        return_type: node.type ? node.type.getText() : null,
        parameters: extractParameters(node.parameters)
    };
}

function extractParameters(params) {
    return params.map(p => ({
        name: p.name.text,
        type: p.type ? p.type.getText() : 'any'
    }));
}

function getModifiers(node) {
    const mods = [];
    if (!node.modifiers) return mods;
    for (const m of node.modifiers) {
        switch (m.kind) {
            case ts.SyntaxKind.PublicKeyword: mods.push('public'); break;
            case ts.SyntaxKind.PrivateKeyword: mods.push('private'); break;
            case ts.SyntaxKind.ProtectedKeyword: mods.push('protected'); break;
            case ts.SyntaxKind.StaticKeyword: mods.push('static'); break;
            case ts.SyntaxKind.AbstractKeyword: mods.push('abstract'); break;
            case ts.SyntaxKind.AsyncKeyword: mods.push('async'); break;
            case ts.SyntaxKind.ReadonlyKeyword: mods.push('readonly'); break;
        }
    }
    return mods;
}

function getDecoratorName(decorator) {
    const expr = decorator.expression;
    if (ts.isCallExpression(expr)) {
        return expr.expression.getText();
    }
    if (ts.isIdentifier(expr)) {
        return expr.text;
    }
    return expr.getText();
}

function getPropertyName(name) {
    if (ts.isIdentifier(name)) return name.text;
    if (ts.isStringLiteral(name)) return name.text;
    if (ts.isComputedPropertyName(name)) return name.getText();
    return name.getText();
}

function countLines(node, sourceFile) {
    const text = node.getText(sourceFile);
    return (text.match(/\n/g) || []).length + 1;
}

// ── Helpers ─────────────────────────────────────────────────

function findTsFiles(dir) {
    const results = [];
    const exclude = ['node_modules', '.git', 'dist', 'build', '.next', '.nuxt', 'coverage'];
    function walk(d) {
        if (!existsSync(d)) return;
        const entries = readdirSync(d, { withFileTypes: true });
        for (const entry of entries) {
            if (exclude.includes(entry.name)) continue;
            const full = join(d, entry.name);
            if (entry.isDirectory()) {
                walk(full);
            } else if (entry.isFile()) {
                const ext = extname(entry.name);
                if (['.ts', '.tsx', '.vue'].includes(ext)) {
                    results.push(full);
                }
            }
        }
    }
    walk(dir);
    return results;
}

function parseTsConfig(tsconfigPath) {
    const raw = readFileSync(tsconfigPath, 'utf-8');
    const parsed = ts.parseConfigFileTextToJson(tsconfigPath, raw);
    if (parsed.error) {
        return getDefaultOptions();
    }
    const basePath = dirname(tsconfigPath);
    const config = ts.parseJsonConfigFileContent(parsed.config, ts.sys, basePath);
    return config.options;
}

function getDefaultOptions() {
    return {
        target: ts.ScriptTarget.Latest,
        module: ts.ModuleKind.ESNext,
        moduleResolution: ts.ModuleResolutionKind.Bundler,
        allowJs: true,
        jsx: ts.JsxEmit.ReactJSX,
        experimentalDecorators: true,
        emitDecoratorMetadata: true,
        noEmit: true
    };
}
