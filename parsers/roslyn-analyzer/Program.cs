using System.Text.Json;
using System.Text.Json.Serialization;
using RoslynAnalyzer.Extractors;

// Manual arg parsing: dotnet run --project RoslynAnalyzer -- --project <path> [--target <csproj>] [--files f1.cs f2.cs]
string? projectPath = null;
string? targetPath = null;
var fileList = new List<string>();

var argsList = new List<string>(args);
for (int i = 0; i < argsList.Count; i++)
{
    switch (argsList[i])
    {
        case "--project" or "-p" when i + 1 < argsList.Count:
            projectPath = argsList[++i];
            break;
        case "--target" or "-t" when i + 1 < argsList.Count:
            targetPath = argsList[++i];
            break;
        case "--files" or "-f":
            while (i + 1 < argsList.Count && !argsList[i + 1].StartsWith("--"))
                fileList.Add(argsList[++i]);
            break;
    }
}

if (string.IsNullOrEmpty(projectPath))
{
    var error = new { errors = new[] { new { file = "", message = "Missing required argument: --project" } } };
    Console.WriteLine(JsonSerializer.Serialize(error));
    return 1;
}

try
{
    var analyzer = new Analyzer(projectPath, targetPath, fileList);
    var result = await analyzer.AnalyzeAsync();

    var options = new JsonSerializerOptions
    {
        WriteIndented = false,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    Console.WriteLine(JsonSerializer.Serialize(result, options));
}
catch (Exception ex)
{
    var error = new { errors = new[] { new { file = "", message = ex.ToString() } }, files = Array.Empty<object>() };
    Console.Error.WriteLine(ex.Message);
    Console.WriteLine(JsonSerializer.Serialize(error));
    return 1;
}

return 0;
