#include "../../src/formats/ModelCfg.h"

#include <filesystem>
#include <iostream>
#include <stdexcept>

namespace
{
void require(bool condition, const char* message)
{
    if (!condition) {
        throw std::runtime_error(message);
    }
}
}

int main(int argc, char** argv)
{
    if (argc < 3) {
        std::cerr << "Usage: model_cfg_test <input-model.cfg> <output-model.cfg>\n";
        return 2;
    }

    const a3ob::cfg::Config config = a3ob::cfg::Config::readFile(argv[1]);
    const std::vector<a3ob::cfg::Skeleton> skeletons = config.skeletons();
    require(skeletons.size() == 1, "Expected one skeleton");
    require(skeletons[0].bones.size() == 18, "Expected 18 skeleton bones");

    a3ob::cfg::Skeleton skeleton;
    skeleton.name = "Skeleton";
    skeleton.bones.push_back({"bone_0", ""});
    for (int i = 0; i < 10; ++i) {
        skeleton.bones.push_back({"bone_" + std::to_string(i + 1), "bone_0"});
    }

    const a3ob::cfg::Config output = a3ob::cfg::Config::skeletonConfig(skeleton);
    output.writeFile(argv[2]);

    const a3ob::cfg::Config reread = a3ob::cfg::Config::readFile(argv[2]);
    const std::vector<a3ob::cfg::Skeleton> exported = reread.skeletons();
    require(exported.size() == 1, "Expected one exported skeleton");
    require(exported[0].bones.size() == 11, "Expected 11 exported bones");

    std::cout << "OK model.cfg skeletons=" << skeletons.size() << " bones=" << skeletons[0].bones.size() << '\n';
    return 0;
}
