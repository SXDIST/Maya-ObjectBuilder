#pragma once

#include <maya/MDGModifier.h>
#include <maya/MDagModifier.h>
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
    bool isUndoable() const override { return true; }
    MStatus undoIt() override;
    MStatus redoIt() override;
private:
    MDGModifier m_modifier;
};

class SetMaterialCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obSetMaterial";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
    bool isUndoable() const override { return true; }
    MStatus undoIt() override;
    MStatus redoIt() override;
private:
    MDGModifier m_modifier;
};

class SetFlagCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obSetFlag";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
    bool isUndoable() const override { return true; }
    MStatus undoIt() override;
    MStatus redoIt() override;
private:
    MDGModifier m_modifier;
};

class FindComponentsCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obFindComponents";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
    bool isUndoable() const override { return true; }
    MStatus undoIt() override;
    MStatus redoIt() override;
private:
    MDGModifier m_modifier;
};

class CreateLODCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obCreateLOD";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
    bool isUndoable() const override { return true; }
    MStatus undoIt() override;
    MStatus redoIt() override;
private:
    MDagModifier m_modifier;
};

class ProxyCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obProxy";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
    bool isUndoable() const override { return true; }
    MStatus undoIt() override;
    MStatus redoIt() override;
private:
    MDagModifier m_modifier;
};

class NamedPropertyCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obNamedProperty";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
    bool isUndoable() const override { return true; }
    MStatus undoIt() override;
    MStatus redoIt() override;
private:
    MDGModifier m_modifier;
};

class UpdateProxyCommand final : public MPxCommand
{
public:
    static constexpr const char* kName = "a3obUpdateProxy";
    static void* creator();
    static MSyntax syntax();
    MStatus doIt(const MArgList& args) override;
    bool isUndoable() const override { return true; }
    MStatus undoIt() override;
    MStatus redoIt() override;
private:
    MDGModifier m_modifier;
};
