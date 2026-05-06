cmake_minimum_required(VERSION 3.13)

project(MayaObjectBuilder VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(MAYA_OBJECT_BUILDER_BUILD_TESTS "Build pure C++ tests" ON)

if(DEFINED ENV{DEVKIT_LOCATION})
    set(MAYA_DEVKIT_LOCATION $ENV{DEVKIT_LOCATION})
else()
    set(MAYA_DEVKIT_LOCATION "C:/maya_devkits/2027/devkitBase")
    set(ENV{DEVKIT_LOCATION} "${MAYA_DEVKIT_LOCATION}")
endif()

include(${MAYA_DEVKIT_LOCATION}/cmake/pluginEntry.cmake)

set(PROJECT_NAME MayaObjectBuilder)

set(FORMAT_SOURCE_FILES
    src/formats/BinaryIO.cpp
    src/formats/BinaryIO.h
    src/formats/P3D.cpp
    src/formats/P3D.h
    src/formats/ModelCfg.cpp
    src/formats/ModelCfg.h
)

set(SOURCE_FILES
    src/PluginMain.cpp
    src/commands/ModelCfgCommands.cpp
    src/commands/ModelCfgCommands.h
    src/translators/P3DTranslator.cpp
    src/translators/P3DTranslator.h
    src/commands/StubCommands.cpp
    src/commands/StubCommands.h
    src/maya/MayaMeshImport.cpp
    src/maya/MayaMeshImport.h
    src/maya/MayaMeshExport.cpp
    src/maya/MayaMeshExport.h
    ${FORMAT_SOURCE_FILES}
)

set(LIBRARIES
    OpenMaya
    OpenMayaAnim
    OpenMayaUI
    Foundation
)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

build_plugin()

if(MAYA_OBJECT_BUILDER_BUILD_TESTS)
    add_executable(p3d_roundtrip tests/cpp/p3d_roundtrip.cpp ${FORMAT_SOURCE_FILES})
    target_include_directories(p3d_roundtrip PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

    add_executable(model_cfg_test tests/cpp/model_cfg_test.cpp ${FORMAT_SOURCE_FILES})
    target_include_directories(model_cfg_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)
endif()
