// CopyHook.h : ICopyHook implementation (Pure Win32)

#pragma once

#include "stdafx.h"

class CFastFileOpCopyHook : public ICopyHookW, public RefCount
{
public:
    CFastFileOpCopyHook() {}
    virtual ~CFastFileOpCopyHook() {}

    // IUnknown
    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) override
    {
        if (riid == IID_IUnknown || riid == IID_ICopyHookW)
        {
            *ppv = static_cast<ICopyHookW*>(this);
            AddRef();
            return S_OK;
        }
        *ppv = NULL;
        return E_NOINTERFACE;
    }

    STDMETHODIMP_(ULONG) AddRef() override { return RefCount::AddRef(); }
    STDMETHODIMP_(ULONG) Release() override { return RefCount::Release(); }

    // ICopyHookW
    UINT STDMETHODCALLTYPE CopyCallback(
        HWND hwnd,
        UINT wFunc,
        UINT wFlags,
        LPCWSTR pszSrcFile,
        DWORD dwSrcAttribs,
        LPCWSTR pszDestFile,
        DWORD dwDestAttribs) override;

private:
    bool SendToPython(const std::wstring& action, const std::wstring& src, const std::wstring& dst);
};

// Class Factory
class CCopyHookClassFactory : public IClassFactory, public RefCount
{
public:
    // IUnknown
    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) override
    {
        if (riid == IID_IUnknown || riid == IID_IClassFactory)
        {
            *ppv = static_cast<IClassFactory*>(this);
            AddRef();
            return S_OK;
        }
        *ppv = NULL;
        return E_NOINTERFACE;
    }

    STDMETHODIMP_(ULONG) AddRef() override { return RefCount::AddRef(); }
    STDMETHODIMP_(ULONG) Release() override { return RefCount::Release(); }

    // IClassFactory
    STDMETHODIMP CreateInstance(IUnknown* pUnkOuter, REFIID riid, void** ppv) override
    {
        if (pUnkOuter) return CLASS_E_NOAGGREGATION;

        CFastFileOpCopyHook* pObj = new CFastFileOpCopyHook();
        if (!pObj) return E_OUTOFMEMORY;

        HRESULT hr = pObj->QueryInterface(riid, ppv);
        pObj->Release();
        return hr;
    }

    STDMETHODIMP LockServer(BOOL fLock) override
    {
        return S_OK;
    }
};
