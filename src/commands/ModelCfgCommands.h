#pragma once

#include <maya/MPxCommand.h>
#include <maya/MSyntax.h>

class ImportModelCfgCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obImportModelCfg";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};

class ExportModelCfgCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obExportModelCfg";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};
