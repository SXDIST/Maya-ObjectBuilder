#include "../../src/formats/P3D.h"

#include <filesystem>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
void require(bool condition, const std::string& message)
{
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::map<std::string, int> taggSummary(const a3ob::p3d::LOD& lod)
{
    std::map<std::string, int> summary;
    for (const a3ob::p3d::Tagg& tagg : lod.taggs) {
        if (!tagg.data) {
            continue;
        }
        switch (tagg.data->kind()) {
        case a3ob::p3d::TaggKind::Property:
            ++summary["#Property#"];
            break;
        case a3ob::p3d::TaggKind::Mass:
            ++summary["#Mass#"];
            break;
        case a3ob::p3d::TaggKind::SharpEdges:
            ++summary["#SharpEdges#"];
            break;
        case a3ob::p3d::TaggKind::UVSet:
            ++summary["#UVSet#"];
            break;
        case a3ob::p3d::TaggKind::Selection:
            ++summary[tagg.name];
            break;
        default:
            break;
        }
    }
    return summary;
}

void checkFile(const std::filesystem::path& input, const std::filesystem::path& outputDir)
{
    const a3ob::p3d::MLOD first = a3ob::p3d::MLOD::readFile(input);
    require(!first.lods.empty(), input.string() + " has no LODs");

    const std::filesystem::path output = outputDir / (input.stem().string() + "_roundtrip.p3d");
    first.writeFile(output);

    const a3ob::p3d::MLOD second = a3ob::p3d::MLOD::readFile(output);
    require(first.lods.size() == second.lods.size(), input.string() + " LOD count changed");

    for (std::size_t i = 0; i < first.lods.size(); ++i) {
        const auto& a = first.lods[i];
        const auto& b = second.lods[i];
        require(a.vertices.size() == b.vertices.size(), input.string() + " vertex count changed");
        require(a.normals.size() == b.normals.size(), input.string() + " normal count changed");
        require(a.faces.size() == b.faces.size(), input.string() + " face count changed");
        require(a.taggs.size() == b.taggs.size(), input.string() + " TAGG count changed");
        require(taggSummary(a) == taggSummary(b), input.string() + " TAGG summary changed");
        require(a.resolution.lod == b.resolution.lod, input.string() + " LOD type changed");
        require(a.resolution.resolution == b.resolution.resolution, input.string() + " LOD resolution changed");
    }

    std::cout << "OK " << input.filename().string() << " lods=" << first.lods.size() << '\n';
}
}

int main(int argc, char** argv)
{
    if (argc < 3) {
        std::cerr << "Usage: p3d_roundtrip <fixtures-p3d-dir> <output-dir>\n";
        return 2;
    }

    const std::filesystem::path fixtures = argv[1];
    const std::filesystem::path outputDir = argv[2];
    std::filesystem::create_directories(outputDir);

    std::size_t count = 0;
    for (const auto& entry : std::filesystem::directory_iterator(fixtures)) {
        if (entry.path().extension() == ".p3d") {
            checkFile(entry.path(), outputDir);
            ++count;
        }
    }

    require(count > 0, "No .p3d fixtures found");
    return 0;
}
