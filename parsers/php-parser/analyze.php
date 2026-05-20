<?php
/**
 * PHP AST Parser for Context Builder Agent.
 * Uses nikic/php-parser to extract structure from PHP files.
 *
 * Usage: php analyze.php <project_path> [file1.php file2.php ...]
 * Output: JSON on stdout
 */

require_once __DIR__ . '/vendor/autoload.php';

use PhpParser\Node;
use PhpParser\Node\Stmt;
use PhpParser\NodeTraverser;
use PhpParser\NodeVisitor\NameResolver;
use PhpParser\NodeVisitorAbstract;
use PhpParser\ParserFactory;
use PhpParser\Error;

if ($argc < 2) {
    fwrite(STDERR, "Usage: php analyze.php <project_path> [files...]\n");
    exit(1);
}

$projectPath = realpath($argv[1]);
$specificFiles = array_slice($argv, 2);

// Find PHP files
if (empty($specificFiles)) {
    $phpFiles = findPhpFiles($projectPath);
} else {
    $phpFiles = $specificFiles;
}

$result = ['files' => [], 'errors' => []];

$parser = (new ParserFactory())->createForHostVersion();
$nameResolver = new NameResolver();
$extractor = new StructExtractor($projectPath);

foreach ($phpFiles as $file) {
    if (!file_exists($file)) continue;
    if (!str_ends_with($file, '.php')) continue;

    try {
        $code = file_get_contents($file);
        if ($code === false) continue;

        $ast = $parser->parse($code);
        if ($ast === null) continue;

        // Resolve names (FQN for classes, functions, etc.)
        $traverser = new NodeTraverser();
        $traverser->addVisitor($nameResolver);
        $ast = $traverser->traverse($ast);

        $fileInfo = $extractor->extract($file, $ast);
        $result['files'][] = $fileInfo;
    } catch (Error $e) {
        $result['errors'][] = [
            'file' => makeRelative($file, $projectPath),
            'message' => $e->getMessage()
        ];
    } catch (\Exception $e) {
        $result['errors'][] = [
            'file' => makeRelative($file, $projectPath),
            'message' => $e->getMessage()
        ];
    }
}

echo json_encode($result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
exit(0);

// ── Helper functions ────────────────────────────────────────

function findPhpFiles(string $dir): array {
    $files = [];
    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($dir, RecursiveDirectoryIterator::SKIP_DOTS)
    );
    $exclude = ['/vendor/', '/node_modules/', '/.git/', '/storage/', '/cache/'];
    foreach ($iterator as $file) {
        if ($file->getExtension() !== 'php') continue;
        $path = $file->getPathname();
        foreach ($exclude as $ex) {
            if (str_contains($path, $ex)) continue 2;
        }
        $files[] = $path;
    }
    return $files;
}

function makeRelative(string $path, string $base): string {
    $path = str_replace('\\', '/', $path);
    $base = str_replace('\\', '/', $base);
    if (str_starts_with($path, $base . '/')) {
        return substr($path, strlen($base) + 1);
    }
    return basename($path);
}

// ── AST Extractor ───────────────────────────────────────────

class StructExtractor {
    private string $projectPath;

    public function __construct(string $projectPath) {
        $this->projectPath = $projectPath;
    }

    public function extract(string $filePath, array $stmts): array {
        $relPath = makeRelative($filePath, $this->projectPath);

        $info = [
            'path' => $relPath,
            'namespace' => null,
            'uses' => [],
            'classes' => [],
        ];

        foreach ($stmts as $stmt) {
            if ($stmt instanceof Stmt\Namespace_) {
                $info['namespace'] = $stmt->name ? $stmt->name->toString() : null;
                $this->processStatements($stmt->stmts, $info);
            } elseif ($stmt instanceof Stmt\Use_) {
                foreach ($stmt->uses as $use) {
                    $info['uses'][] = $use->name->toString();
                }
            } elseif ($stmt instanceof Stmt\Class_ || $stmt instanceof Stmt\Interface_ || $stmt instanceof Stmt\Trait_ || $stmt instanceof Stmt\Enum_) {
                $this->processStatements([$stmt], $info);
            } elseif ($stmt instanceof Stmt\Use_) {
                foreach ($stmt->uses as $use) {
                    $info['uses'][] = $use->name->toString();
                }
            }
        }

        return $info;
    }

    private function processStatements(array $stmts, array &$info): void {
        foreach ($stmts as $stmt) {
            if ($stmt instanceof Stmt\Class_) {
                $info['classes'][] = $this->extractClass($stmt, 'class');
            } elseif ($stmt instanceof Stmt\Interface_) {
                $info['classes'][] = $this->extractClass($stmt, 'interface');
            } elseif ($stmt instanceof Stmt\Trait_) {
                $info['classes'][] = $this->extractClass($stmt, 'trait');
            } elseif ($stmt instanceof Stmt\Enum_) {
                $info['classes'][] = $this->extractClass($stmt, 'enum');
            } elseif ($stmt instanceof Stmt\Use_) {
                foreach ($stmt->uses as $use) {
                    $info['uses'][] = $use->name->toString();
                }
            }
        }
    }

    private function extractClass($classStmt, string $type): array {
        $class = [
            'name' => $classStmt->name ? $classStmt->name->toString() : 'anonymous',
            'type' => $type,
            'extends' => [],
            'implements' => [],
            'attributes' => [],
            'methods' => [],
            'constructors' => [],
            'properties' => [],
            'loc' => $classStmt->getEndLine() - $classStmt->getStartLine() + 1,
        ];

        // Attributes (PHP 8)
        if (property_exists($classStmt, 'attrGroups') && $classStmt->attrGroups) {
            foreach ($classStmt->attrGroups as $attrGroup) {
                foreach ($attrGroup->attrs as $attr) {
                    $class['attributes'][] = $attr->name->toString();
                }
            }
        }

        // Base class
        if ($type === 'class' && $classStmt->extends) {
            $class['extends'][] = $classStmt->extends->toString();
        }

        // Interfaces
        if (property_exists($classStmt, 'implements')) {
            foreach ($classStmt->implements as $iface) {
                $class['implements'][] = $iface->toString();
            }
        }

        // Members
        foreach ($classStmt->stmts ?? [] as $member) {
            if ($member instanceof Stmt\ClassMethod) {
                $method = $this->extractMethod($member);
                if ($member->name->toString() === '__construct') {
                    $class['constructors'][] = ['parameters' => $method['parameters'], 'modifiers' => $method['modifiers']];
                }
                $class['methods'][] = $method;
            } elseif ($member instanceof Stmt\Property) {
                foreach ($member->props as $prop) {
                    $class['properties'][] = $this->extractProperty($member, $prop);
                }
            }
        }

        return $class;
    }

    private function typeToString($type): string {
        if ($type === null) return 'mixed';
        if ($type instanceof \PhpParser\Node\NullableType) {
            return '?' . $this->typeToString($type->type);
        }
        if ($type instanceof \PhpParser\Node\UnionType) {
            $parts = [];
            foreach ($type->types as $t) $parts[] = $this->typeToString($t);
            return implode('|', $parts);
        }
        if ($type instanceof \PhpParser\Node\IntersectionType) {
            $parts = [];
            foreach ($type->types as $t) $parts[] = $this->typeToString($t);
            return implode('&', $parts);
        }
        if (method_exists($type, 'toString')) {
            return $type->toString();
        }
        return (string)$type;
    }

    private function extractMethod(Stmt\ClassMethod $method): array {
        $params = [];
        foreach ($method->params as $param) {
            $params[] = [
                'name' => $param->var->name ?? '',
                'type' => $this->typeToString($param->type),
            ];
        }

        $modifiers = [];
        if ($method->isPublic()) $modifiers[] = 'public';
        if ($method->isProtected()) $modifiers[] = 'protected';
        if ($method->isPrivate()) $modifiers[] = 'private';
        if ($method->isStatic()) $modifiers[] = 'static';
        if ($method->isAbstract()) $modifiers[] = 'abstract';
        if ($method->isFinal()) $modifiers[] = 'final';

        return [
            'name' => $method->name->toString(),
            'return_type' => $this->typeToString($method->returnType),
            'parameters' => $params,
            'modifiers' => $modifiers,
            'attributes' => [],
            'loc' => $method->getEndLine() - $method->getStartLine() + 1,
        ];
    }

    private function extractProperty(Stmt\Property $prop, Stmt\PropertyProperty $propDecl): array {
        $modifiers = [];
        if ($prop->isPublic()) $modifiers[] = 'public';
        if ($prop->isProtected()) $modifiers[] = 'protected';
        if ($prop->isPrivate()) $modifiers[] = 'private';
        if ($prop->isStatic()) $modifiers[] = 'static';
        if ($prop->isReadonly()) $modifiers[] = 'readonly';

        $attrs = [];
        if (property_exists($prop, 'attrGroups') && $prop->attrGroups) {
            foreach ($prop->attrGroups as $ag) {
                foreach ($ag->attrs as $a) {
                    $attrs[] = $a->name->toString();
                }
            }
        }

        return [
            'name' => $propDecl->name->toString(),
            'type' => $this->typeToString($prop->type),
            'modifiers' => $modifiers,
            'attributes' => $attrs,
        ];
    }
}
