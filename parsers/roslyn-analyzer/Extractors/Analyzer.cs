using System.Text.Json.Serialization;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.MSBuild;
using Microsoft.Build.Locator;

namespace RoslynAnalyzer.Extractors;

// ── Output models ──────────────────────────────────────────

public class AnalysisResult
{
    [JsonPropertyName("files")]
    public List<FileResult> Files { get; set; } = new();

    [JsonPropertyName("errors")]
    public List<ParseError> Errors { get; set; } = new();
}

public class FileResult
{
    [JsonPropertyName("path")]
    public string Path { get; set; } = "";

    [JsonPropertyName("namespace")]
    public string? Namespace { get; set; }

    [JsonPropertyName("usings")]
    public List<string> Usings { get; set; } = new();

    [JsonPropertyName("classes")]
    public List<ClassResult> Classes { get; set; } = new();
}

public class ClassResult
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("type")]
    public string Type { get; set; } = "class";

    [JsonPropertyName("base_types")]
    public List<string> BaseTypes { get; set; } = new();

    [JsonPropertyName("interfaces")]
    public List<string> Interfaces { get; set; } = new();

    [JsonPropertyName("attributes")]
    public List<string> Attributes { get; set; } = new();

    [JsonPropertyName("methods")]
    public List<MethodResult> Methods { get; set; } = new();

    [JsonPropertyName("constructors")]
    public List<ConstructorResult> Constructors { get; set; } = new();

    [JsonPropertyName("properties")]
    public List<PropertyResult> Properties { get; set; } = new();

    [JsonPropertyName("fields")]
    public List<FieldResult> Fields { get; set; } = new();

    [JsonPropertyName("loc")]
    public int Loc { get; set; }
}

public class MethodResult
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("return_type")]
    public string? ReturnType { get; set; }

    [JsonPropertyName("parameters")]
    public List<ParameterResult> Parameters { get; set; } = new();

    [JsonPropertyName("modifiers")]
    public List<string> Modifiers { get; set; } = new();

    [JsonPropertyName("attributes")]
    public List<string> Attributes { get; set; } = new();

    [JsonPropertyName("loc")]
    public int Loc { get; set; }
}

public class ConstructorResult
{
    [JsonPropertyName("parameters")]
    public List<ParameterResult> Parameters { get; set; } = new();

    [JsonPropertyName("modifiers")]
    public List<string> Modifiers { get; set; } = new();

    [JsonPropertyName("attributes")]
    public List<string> Attributes { get; set; } = new();
}

public class ParameterResult
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("type")]
    public string Type { get; set; } = "object";
}

public class PropertyResult
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("modifiers")]
    public List<string> Modifiers { get; set; } = new();

    [JsonPropertyName("attributes")]
    public List<string> Attributes { get; set; } = new();
}

public class FieldResult
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("modifiers")]
    public List<string> Modifiers { get; set; } = new();

    [JsonPropertyName("attributes")]
    public List<string> Attributes { get; set; } = new();
}

public class ParseError
{
    [JsonPropertyName("file")]
    public string File { get; set; } = "";

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
}

// ── Analyzer ───────────────────────────────────────────────

public class Analyzer
{
    private readonly string _projectPath;
    private readonly string? _targetPath;
    private readonly List<string>? _fileList;

    public Analyzer(string projectPath, string? targetPath, List<string>? fileList)
    {
        _projectPath = Path.GetFullPath(projectPath);
        _targetPath = targetPath;
        _fileList = fileList;
    }

    public async Task<AnalysisResult> AnalyzeAsync()
    {
        var result = new AnalysisResult();

        if (_fileList is { Count: > 0 })
        {
            // Analyze specific files (loose files, no project context)
            await AnalyzeFilesAsync(_fileList, result);
        }
        else if (_targetPath is not null && File.Exists(_targetPath))
        {
            // Analyze via MSBuild (full project context)
            await AnalyzeWithMSBuildAsync(_targetPath, result);
        }
        else
        {
            // Find all .cs files and analyze them individually
            var csFiles = Directory.GetFiles(_projectPath, "*.cs", SearchOption.AllDirectories)
                .Where(f => !f.Contains("\\obj\\") && !f.Contains("\\bin\\")
                         && !f.Contains("\\Library\\") && !f.Contains("\\Temp\\"))
                .ToList();

            await AnalyzeFilesAsync(csFiles, result);
        }

        return result;
    }

    private async Task AnalyzeWithMSBuildAsync(string projectOrSolution, AnalysisResult result)
    {
        try
        {
            // Try MSBuild first
            MSBuildLocator.RegisterDefaults();
            using var workspace = MSBuildWorkspace.Create();
            workspace.WorkspaceFailed += (_, args) =>
            {
                if (args.Diagnostic.Kind == WorkspaceDiagnosticKind.Failure)
                    result.Errors.Add(new ParseError { File = "", Message = args.Diagnostic.Message });
            };

            Solution? solution = null;
            Project? project = null;

            if (projectOrSolution.EndsWith(".sln", StringComparison.OrdinalIgnoreCase))
            {
                solution = await workspace.OpenSolutionAsync(projectOrSolution);
                if (solution.Projects.Any())
                    project = solution.Projects.First();
            }
            else
            {
                project = await workspace.OpenProjectAsync(projectOrSolution);
            }

            if (project is not null)
            {
                var compilation = await project.GetCompilationAsync();
                if (compilation is not null)
                {
                    foreach (var tree in compilation.SyntaxTrees)
                    {
                        ProcessSyntaxTree(tree, compilation, result);
                    }
                }
            }
        }
        catch (Exception ex)
        {
            // MSBuild failed — fall back to direct file analysis
            result.Errors.Add(new ParseError
            {
                File = "",
                Message = $"MSBuild failed, falling back to direct parsing: {ex.Message}"
            });
            var csFiles = Directory.GetFiles(_projectPath, "*.cs", SearchOption.AllDirectories)
                .Where(f => !f.Contains("\\obj\\") && !f.Contains("\\bin\\")
                         && !f.Contains("\\Library\\"))
                .ToList();
            await AnalyzeFilesAsync(csFiles, result);
        }
    }

    private Task AnalyzeFilesAsync(List<string> files, AnalysisResult result)
    {
        foreach (var file in files)
        {
            try
            {
                var code = File.ReadAllText(file);
                var tree = CSharpSyntaxTree.ParseText(code, path: file);
                var root = tree.GetCompilationUnitRoot();

                var compilation = CSharpCompilation.Create("Analysis")
                    .AddReferences(MetadataReference.CreateFromFile(typeof(object).Assembly.Location))
                    .AddSyntaxTrees(tree);

                ProcessSyntaxTree(tree, compilation, result);
            }
            catch (Exception ex)
            {
                var relPath = GetRelativePath(file);
                result.Errors.Add(new ParseError { File = relPath, Message = ex.Message });
            }
        }

        return Task.CompletedTask;
    }

    private void ProcessSyntaxTree(SyntaxTree tree, Compilation compilation, AnalysisResult result)
    {
        var filePath = tree.FilePath;
        if (string.IsNullOrEmpty(filePath))
            filePath = "unknown.cs";

        var relPath = GetRelativePath(filePath);
        var root = tree.GetCompilationUnitRoot();
        var semanticModel = compilation.GetSemanticModel(tree);

        var fileResult = new FileResult
        {
            Path = relPath
        };

        // Namespace
        var namespaceDecl = root.Members.OfType<NamespaceDeclarationSyntax>().FirstOrDefault()
            ?? (MemberDeclarationSyntax?)root.Members.OfType<FileScopedNamespaceDeclarationSyntax>().FirstOrDefault();

        if (namespaceDecl is NamespaceDeclarationSyntax ns)
            fileResult.Namespace = ns.Name.ToString();
        else if (namespaceDecl is FileScopedNamespaceDeclarationSyntax fns)
            fileResult.Namespace = fns.Name.ToString();

        // Usings
        foreach (var usingDirective in root.Usings)
            fileResult.Usings.Add(usingDirective.Name?.ToString() ?? usingDirective.NamespaceOrType.ToString());

        // Find all class/interface/record/struct declarations
        var typeDeclarations = root.DescendantNodes()
            .OfType<TypeDeclarationSyntax>()
            .Where(t => t.Parent is NamespaceDeclarationSyntax
                     || t.Parent is FileScopedNamespaceDeclarationSyntax
                     || t.Parent is CompilationUnitSyntax);

        foreach (var typeDecl in typeDeclarations)
        {
            var classResult = ExtractClass(typeDecl);
            fileResult.Classes.Add(classResult);
        }

        result.Files.Add(fileResult);
    }

    private ClassResult ExtractClass(TypeDeclarationSyntax typeDecl)
    {
        var classResult = new ClassResult
        {
            Name = typeDecl.Identifier.Text,
            Type = typeDecl.Keyword.Text,  // class, interface, record, struct
            Loc = typeDecl.GetText().Lines.Count
        };

        // Base types & interfaces
        if (typeDecl.BaseList is not null)
        {
            foreach (var baseType in typeDecl.BaseList.Types)
            {
                var name = baseType.Type.ToString();
                // Heuristic: interfaces usually start with I
                if (name.StartsWith("I") && name.Length > 1 && char.IsUpper(name[1]))
                    classResult.Interfaces.Add(name);
                else
                    classResult.BaseTypes.Add(name);
            }
        }

        // Attributes
        foreach (var attrList in typeDecl.AttributeLists)
        foreach (var attr in attrList.Attributes)
            classResult.Attributes.Add(attr.Name.ToString());

        // Methods
        foreach (var method in typeDecl.Members.OfType<MethodDeclarationSyntax>()
                     .Where(m => !IsPropertyOrEvent(m)))
        {
            classResult.Methods.Add(ExtractMethod(method));
        }

        // Constructors
        foreach (var ctor in typeDecl.Members.OfType<ConstructorDeclarationSyntax>())
        {
            classResult.Constructors.Add(ExtractConstructor(ctor));
        }

        // Properties
        foreach (var prop in typeDecl.Members.OfType<PropertyDeclarationSyntax>())
        {
            classResult.Properties.Add(ExtractProperty(prop));
        }

        // Fields
        foreach (var field in typeDecl.Members.OfType<FieldDeclarationSyntax>())
        {
            foreach (var variable in field.Declaration.Variables)
            {
                classResult.Fields.Add(new FieldResult
                {
                    Name = variable.Identifier.Text,
                    Type = field.Declaration.Type.ToString(),
                    Modifiers = field.Modifiers.Select(m => m.Text).ToList(),
                    Attributes = field.AttributeLists
                        .SelectMany(al => al.Attributes.Select(a => a.Name.ToString())).ToList()
                });
            }
        }

        return classResult;
    }

    private MethodResult ExtractMethod(MethodDeclarationSyntax method)
    {
        return new MethodResult
        {
            Name = method.Identifier.Text,
            ReturnType = method.ReturnType.ToString(),
            Parameters = method.ParameterList.Parameters.Select(p => new ParameterResult
            {
                Name = p.Identifier.Text,
                Type = p.Type?.ToString() ?? "object"
            }).ToList(),
            Modifiers = method.Modifiers.Select(m => m.Text).ToList(),
            Attributes = method.AttributeLists
                .SelectMany(al => al.Attributes.Select(a => a.Name.ToString())).ToList(),
            Loc = method.GetText().Lines.Count
        };
    }

    private ConstructorResult ExtractConstructor(ConstructorDeclarationSyntax ctor)
    {
        return new ConstructorResult
        {
            Parameters = ctor.ParameterList.Parameters.Select(p => new ParameterResult
            {
                Name = p.Identifier.Text,
                Type = p.Type?.ToString() ?? "object"
            }).ToList(),
            Modifiers = ctor.Modifiers.Select(m => m.Text).ToList(),
            Attributes = ctor.AttributeLists
                .SelectMany(al => al.Attributes.Select(a => a.Name.ToString())).ToList(),
        };
    }

    private PropertyResult ExtractProperty(PropertyDeclarationSyntax prop)
    {
        return new PropertyResult
        {
            Name = prop.Identifier.Text,
            Type = prop.Type.ToString(),
            Modifiers = prop.Modifiers.Select(m => m.Text).ToList(),
            Attributes = prop.AttributeLists
                .SelectMany(al => al.Attributes.Select(a => a.Name.ToString())).ToList(),
        };
    }

    private static bool IsPropertyOrEvent(MethodDeclarationSyntax method)
    {
        // Skip accessor methods (get_, set_, add_, remove_)
        var name = method.Identifier.Text;
        return name.StartsWith("get_") || name.StartsWith("set_")
            || name.StartsWith("add_") || name.StartsWith("remove_");
    }

    private string GetRelativePath(string filePath)
    {
        try
        {
            var full = Path.GetFullPath(filePath);
            var basePath = Path.GetFullPath(_projectPath).TrimEnd(Path.DirectorySeparatorChar);
            if (full.StartsWith(basePath, StringComparison.OrdinalIgnoreCase))
            {
                var rel = full[basePath.Length..].TrimStart(Path.DirectorySeparatorChar);
                return rel.Replace('\\', '/');
            }
            return Path.GetFileName(filePath);
        }
        catch
        {
            return Path.GetFileName(filePath);
        }
    }
}
