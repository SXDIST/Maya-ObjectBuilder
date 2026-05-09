#pragma once

#include <maya/MPxFileTranslator.h>
#include <maya/MString.h>

class P3DTranslator final : public MPxFileTranslator
{
public:
    static constexpr const char* kTranslatorName = "Arma P3D";

    P3DTranslator() = default;
    ~P3DTranslator() override = default;

    static void* creator();

    bool haveReadMethod() const override;
    bool haveWriteMethod() const override;
    bool haveReferenceMethod() const override;
    bool haveNamespaceSupport() const override;
    bool canBeOpened() const override;
    MString defaultExtension() const override;
    MString filter() const override;

    MFileKind identifyFile(const MFileObject& fileName, const char* buffer, short size) const override;
    MStatus reader(const MFileObject& file, const MString& optionsString, FileAccessMode mode) override;
    MStatus writer(const MFileObject& file, const MString& optionsString, FileAccessMode mode) override;
};
