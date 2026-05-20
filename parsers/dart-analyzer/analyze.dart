/// Dart AST Analyzer for Context Builder Agent.
/// Uses package:analyzer to extract structure from Dart files.
///
/// Usage: dart run analyze.dart <project_path> [file1.dart file2.dart ...]
/// Output: JSON on stdout

import 'dart:convert';
import 'dart:io';

import 'package:analyzer/dart/analysis/analysis_context_collection.dart';
import 'package:analyzer/dart/analysis/results.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/token.dart';
import 'package:analyzer/file_system/physical_file_system.dart';

void main(List<String> args) async {
  if (args.isEmpty) {
    stderr.writeln('Usage: dart run analyze.dart <project_path> [files...]');
    exit(1);
  }

  final projectPath = Directory(args[0]).absolute.path;
  final specificFiles = args.length > 1 ? args.sublist(1) : null;

  final result = <String, dynamic>{'files': <Map<String, dynamic>>[], 'errors': <Map<String, dynamic>>[]};

  try {
    final files = specificFiles ?? findDartFiles(projectPath);
    if (files.isEmpty) {
      stdout.writeln(jsonEncode(result));
      return;
    }

    final resourceProvider = PhysicalResourceProvider.INSTANCE;
    final collection = AnalysisContextCollection(
      includedPaths: [projectPath],
      resourceProvider: resourceProvider,
    );

    for (final filePath in files) {
      try {
        final fullPath = filePath;
        final context = collection.contextFor(fullPath);
        final session = context.currentSession;

        // Get the resolved unit
        final unitResult = await session.getResolvedUnit(fullPath);
        if (unitResult is ResolvedUnitResult) {
          final fileInfo = extractFile(unitResult, fullPath, projectPath);
          (result['files'] as List).add(fileInfo);
        }
      } catch (e) {
        (result['errors'] as List).add({
          'file': _relativePath(filePath, projectPath),
          'message': e.toString(),
        });
      }
    }
  } catch (e) {
    (result['errors'] as List).add({
      'file': '',
      'message': 'Dart analyzer error: $e',
    });
  }

  stdout.writeln(jsonEncode(result));
}

Map<String, dynamic> extractFile(
    ResolvedUnitResult unitResult, String filePath, String projectPath) {
  final relPath = _relativePath(filePath, projectPath);
  final unit = unitResult.unit;
  final info = <String, dynamic>{
    'path': relPath,
    'library': unitResult.libraryElement?.identifier ?? unitResult.libraryElement?.name,
    'imports': <String>[],
    'classes': <Map<String, dynamic>>[],
    'functions': <Map<String, dynamic>>[],
  };

  // Imports
  for (final directive in unit.directives) {
    if (directive is ImportDirective) {
      (info['imports'] as List).add(directive.uri.stringValue ?? directive.uri.toString());
    } else if (directive is ExportDirective) {
      (info['imports'] as List).add(directive.uri.stringValue ?? directive.uri.toString());
    } else if (directive is PartDirective) {
      (info['imports'] as List).add(directive.uri.stringValue ?? directive.uri.toString());
    }
  }

  // Declarations
  for (final declaration in unit.declarations) {
    if (declaration is ClassDeclaration) {
      (info['classes'] as List).add(_extractClass(declaration));
    } else if (declaration is MixinDeclaration) {
      (info['classes'] as List).add(_extractMixin(declaration));
    } else if (declaration is EnumDeclaration) {
      (info['classes'] as List).add(_extractEnum(declaration));
    } else if (declaration is ExtensionDeclaration) {
      (info['classes'] as List).add(_extractExtension(declaration));
    } else if (declaration is FunctionDeclaration) {
      (info['functions'] as List).add(_extractFunction(declaration));
    }
  }

  return info;
}

Map<String, dynamic> _extractClass(ClassDeclaration node) {
  final cls = <String, dynamic>{
    'name': node.name.lexeme,
    'type': 'class',
    'extends': <String>[],
    'implements': <String>[],
    'with': <String>[],
    'annotations': <String>[],
    'methods': <Map<String, dynamic>>[],
    'constructors': <Map<String, dynamic>>[],
    'properties': <Map<String, dynamic>>[],
    'loc': _loc(node),
  };

  _extractAnnotations(node.metadata, cls['annotations']);

  if (node.extendsClause != null) {
    (cls['extends'] as List).add(node.extendsClause!.superclass.name2.lexeme);
  }
  if (node.implementsClause != null) {
    for (final iface in node.implementsClause!.interfaces) {
      (cls['implements'] as List).add(iface.name2.lexeme);
    }
  }
  if (node.withClause != null) {
    for (final mxn in node.withClause!.mixinTypes) {
      (cls['with'] as List).add(mxn.name2.lexeme);
    }
  }

  for (final member in node.members) {
    if (member is MethodDeclaration) {
      (cls['methods'] as List).add(_extractMethod(member));
    } else if (member is ConstructorDeclaration) {
      (cls['constructors'] as List).add(_extractConstructor(member));
    } else if (member is FieldDeclaration) {
      for (final variable in member.fields.variables) {
        (cls['properties'] as List).add(_extractField(member, variable));
      }
    }
  }

  return cls;
}

Map<String, dynamic> _extractMixin(MixinDeclaration node) {
  return {
    'name': node.name.lexeme,
    'type': 'mixin',
    'extends': <String>[],
    'implements': node.implementsClause?.interfaces
            .map((i) => i.name2.lexeme)
            .toList() ??
        <String>[],
    'with': <String>[],
    'annotations': <String>[],
    'methods': node.members
        .whereType<MethodDeclaration>()
        .map(_extractMethod)
        .toList(),
    'constructors': <Map<String, dynamic>>[],
    'properties': <Map<String, dynamic>>[],
    'loc': _loc(node),
  };
}

Map<String, dynamic> _extractEnum(EnumDeclaration node) {
  return {
    'name': node.name.lexeme,
    'type': 'enum',
    'extends': <String>[],
    'implements': <String>[],
    'with': <String>[],
    'annotations': <String>[],
    'methods': node.members
        .whereType<MethodDeclaration>()
        .map(_extractMethod)
        .toList(),
    'constructors': <Map<String, dynamic>>[],
    'properties': <Map<String, dynamic>>[],
    'loc': _loc(node),
  };
}

Map<String, dynamic> _extractExtension(ExtensionDeclaration node) {
  String extendedName = 'dynamic';
  if (node.onClause != null) {
    final et = node.onClause!.extendedType;
    if (et is NamedType) {
      extendedName = et.name2.lexeme;
    } else {
      extendedName = et.toString();
    }
  }
  return {
    'name': node.name?.lexeme ?? 'unnamed',
    'type': 'extension',
    'extends': [extendedName],
    'implements': <String>[],
    'with': <String>[],
    'annotations': <String>[],
    'methods': node.members
        .whereType<MethodDeclaration>()
        .map(_extractMethod)
        .toList(),
    'constructors': <Map<String, dynamic>>[],
    'properties': <Map<String, dynamic>>[],
    'loc': _loc(node),
  };
}

Map<String, dynamic> _extractMethod(MethodDeclaration node) {
  final params = <Map<String, dynamic>>[];
  if (node.parameters != null) {
    for (final p in node.parameters!.parameters) {
      if (p is SimpleFormalParameter) {
        params.add({
          'name': p.name?.lexeme ?? '',
          'type': p.type?.toString() ?? 'dynamic',
        });
      } else if (p is DefaultFormalParameter) {
        final inner = p.parameter;
        if (inner is SimpleFormalParameter) {
          params.add({
            'name': inner.name?.lexeme ?? '',
            'type': inner.type?.toString() ?? 'dynamic',
          });
        }
      }
    }
  }

  return {
    'name': node.name.lexeme,
    'return_type': node.returnType?.toString(),
    'parameters': params,
    'modifiers': _modifiers(node),
    'attributes': <String>[],
    'loc': _loc(node),
  };
}

Map<String, dynamic> _extractConstructor(ConstructorDeclaration node) {
  final params = <Map<String, dynamic>>[];
  if (node.parameters != null) {
    for (final p in node.parameters!.parameters) {
      if (p is SimpleFormalParameter) {
        params.add({
          'name': p.name?.lexeme ?? '',
          'type': p.type?.toString() ?? 'dynamic',
        });
      }
    }
  }

  return {
    'parameters': params,
    'modifiers': _modifiers(node),
  };
}

Map<String, dynamic> _extractField(
    FieldDeclaration field, VariableDeclaration variable) {
  return {
    'name': variable.name.lexeme,
    'type': field.fields.type?.toString(),
    'modifiers': _modifiers(field),
    'attributes': <String>[],
  };
}

Map<String, dynamic> _extractFunction(FunctionDeclaration node) {
  final params = <Map<String, dynamic>>[];
  if (node.functionExpression.parameters != null) {
    for (final p in node.functionExpression.parameters!.parameters) {
      if (p is SimpleFormalParameter) {
        params.add({
          'name': p.name?.lexeme ?? '',
          'type': p.type?.toString() ?? 'dynamic',
        });
      }
    }
  }

  return {
    'name': node.name.lexeme,
    'return_type': node.returnType?.toString(),
    'parameters': params,
  };
}

void _extractAnnotations(
    List<Annotation>? annotations, List<String> output) {
  if (annotations == null) return;
  for (final a in annotations) {
    output.add(a.name.name);
  }
}

List<String> _modifiers(AstNode node) {
  // Dart doesn't have per-member access modifiers on the AST node directly
  // They are embedded in the token stream. For simplicity, return empty.
  final mods = <String>[];
  // Check for static on supported member types
  if (node is MethodDeclaration && node.isStatic) mods.add('static');
  if (node is ConstructorDeclaration && node.isStatic) mods.add('static');
  if (node is FieldDeclaration && node.isStatic) mods.add('static');
  return mods;
}

int _loc(AstNode node) {
  final end = node.endToken?.offset ?? node.offset;
  final start = node.offset;
  return node.root.beginToken.offset == 0 ? 0 : 1; // simplified
}

String _relativePath(String path, String base) {
  path = path.replaceAll('\\', '/');
  base = base.replaceAll('\\', '/');
  if (path.startsWith('$base/')) {
    return path.substring(base.length + 1);
  }
  return path.split('/').last;
}

List<String> findDartFiles(String dir) {
  final files = <String>[];
  final dirObj = Directory(dir);
  if (!dirObj.existsSync()) return files;

  final exclude = ['/build/', '/.dart_tool/', '/.git/', '/.idea/', '/android/', '/ios/'];

  void walk(Directory d) {
    for (final entity in d.listSync(recursive: false)) {
      if (entity is Directory) {
        final path = entity.path.replaceAll('\\', '/');
        if (!exclude.any((ex) => path.contains(ex))) {
          walk(entity);
        }
      } else if (entity is File && entity.path.endsWith('.dart')) {
        files.add(entity.path);
      }
    }
  }

  walk(dirObj);
  return files;
}
