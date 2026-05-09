#pragma once

#include <maya/MPxCommand.h>
#include <maya/MSyntax.h>

class ValidateCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obValidate";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};

class SetMassCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obSetMass";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};

class SetMaterialCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obSetMaterial";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};

class SetFlagCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obSetFlag";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};

class FindComponentsCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obFindComponents";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};

class CreateLODCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obCreateLOD";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};

class ProxyCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obProxy";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};

class NamedPropertyCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obNamedProperty";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};

class UpdateProxyCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obUpdateProxy";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
};
