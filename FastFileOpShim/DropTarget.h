// DropTarget.h : IDropTarget + IShellExtInit 实现
//
// 拦截拖拽操作，通过 IShellExtInit 获取目标文件夹路径
// 通过 Named Pipe 发送请求到 Python 后端处理

#pragma once

#include "stdafx.h"

// 前向声明：DragDropHandler 的 CLSID 在 stdafx.h 中定义
// {C3D4E5F6-A7B8-9012-CDEF-123456789012}

class CFastFileOpDropTarget :
    public IDropTarget,
    public IShellExtInit,
    public RefCount
{
public:
    CFastFileOpDropTarget() {}
    virtual ~CFastFileOpDropTarget() {}

    // IUnknown
    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) override
    {
        if (riid == IID_IUnknown)
        {
            *ppv = static_cast<IUnknown*>(static_cast<IDropTarget*>(this));
            AddRef();
            return S_OK;
        }
        if (riid == IID_IDropTarget)
        {
            *ppv = static_cast<IDropTarget*>(this);
            AddRef();
            return S_OK;
        }
        if (riid == IID_IShellExtInit)
        {
            *ppv = static_cast<IShellExtInit*>(this);
            AddRef();
            return S_OK;
        }
        *ppv = NULL;
        return E_NOINTERFACE;
    }

    STDMETHODIMP_(ULONG) AddRef() override { return RefCount::AddRef(); }
    STDMETHODIMP_(ULONG) Release() override { return RefCount::Release(); }

    // IShellExtInit — Explorer 在创建 DropTarget 时调用，提供目标文件夹 PIDL
    HRESULT STDMETHODCALLTYPE Initialize(
        LPCITEMIDLIST pidlFolder,
        LPDATAOBJECT pDataObj,
        HKEY hkeyProgID) override;

    // IDropTarget
    HRESULT STDMETHODCALLTYPE DragEnter(
        IDataObject* pDataObj,
        DWORD grfKeyState,
        POINTL pt,
        DWORD* pdwEffect) override;

    HRESULT STDMETHODCALLTYPE DragOver(
        DWORD grfKeyState,
        POINTL pt,
        DWORD* pdwEffect) override;

    HRESULT STDMETHODCALLTYPE DragLeave() override;

    HRESULT STDMETHODCALLTYPE Drop(
        IDataObject* pDataObj,
        DWORD grfKeyState,
        POINTL pt,
        DWORD* pdwEffect) override;

private:
    bool m_canDrop = false;
    DWORD m_dropEffect = DROPEFFECT_NONE;
    std::wstring m_targetFolder;

    bool GetDropFiles(IDataObject* pDataObj, std::vector<std::wstring>& files);
    bool SendToPython(const std::wstring& action, const std::vector<std::wstring>& src, const std::wstring& dst);
};
