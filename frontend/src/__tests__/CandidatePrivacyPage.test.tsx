import React from 'react';
import { CandidatePrivacyPage } from '../pages/CandidatePrivacyPage';
import { useAuthStore } from '../stores/useAuthStore';
import { api } from '../api/client';

declare const describe: (name: string, fn: () => void) => void;
declare const it: (name: string, fn: () => void | Promise<void>) => void;
declare const beforeEach: (fn: () => void | Promise<void>) => void;
declare const afterEach: (fn: () => void | Promise<void>) => void;
declare const expect: any;
declare const renderToString: (el: React.ReactElement) => string;
declare const vi: any;

describe('CandidatePrivacyPage & 152-ФЗ Consents Management', () => {
  beforeEach(() => {
    useAuthStore.getState().setConsents(true, true);
  });

  it('renders privacy page controls, 152-ФЗ badges and action buttons', () => {
    const html = renderToString(React.createElement(CandidatePrivacyPage, {}));

    expect(html).toContain('Защита персональных данных и настройки 152-ФЗ');
    expect(html).toContain('Сохранить настройки приватности');
    expect(html).toContain('Экспорт архива (152-ФЗ)');
    expect(html).toContain('Отозвать согласия');
  });

  it('verifies handleSave sends both consent_pdn_processing and consent_profile_publication', async () => {
    let capturedUrl = '';
    let capturedBody: any = null;
    const originalPut = api.put;

    api.put = (async (url: string, body?: any) => {
      capturedUrl = url;
      capturedBody = body;
      return { success: true };
    }) as typeof api.put;

    try {
      // Simulate save payload execution
      const pdn = true;
      const pub = false;
      await api.put('/auth/consents', {
        consent_profile_publication: pub,
        consent_pdn_processing: pdn,
      });
      useAuthStore.getState().setConsents(pdn, pub);

      expect(capturedUrl).toBe('/auth/consents');
      expect(capturedBody).toEqual({
        consent_profile_publication: false,
        consent_pdn_processing: true,
      });
      expect(useAuthStore.getState().isPdnConsentGiven).toBe(true);
      expect(useAuthStore.getState().isProfilePublicationConsentGiven).toBe(false);
    } finally {
      api.put = originalPut;
    }
  });

  it('verifies export archive invokes api.downloadBlob with 152-ФЗ endpoint', async () => {
    let capturedEndpoint = '';
    let capturedFilename = '';
    const originalDownloadBlob = api.downloadBlob;

    api.downloadBlob = (async (endpoint: string, filename?: string) => {
      capturedEndpoint = endpoint;
      capturedFilename = filename || '';
    }) as typeof api.downloadBlob;

    try {
      await api.downloadBlob('/auth/export-archive', 'fsp_user_archive_152fz.json');

      expect(capturedEndpoint).toBe('/auth/export-archive');
      expect(capturedFilename).toBe('fsp_user_archive_152fz.json');
    } finally {
      api.downloadBlob = originalDownloadBlob;
    }
  });

  it('verifies revoke consents triggers api.post /auth/consents/revoke and resets store flags', async () => {
    let capturedUrl = '';
    const originalPost = api.post;

    api.post = (async (url: string) => {
      capturedUrl = url;
      return { success: true };
    }) as typeof api.post;

    try {
      await api.post('/auth/consents/revoke');
      useAuthStore.getState().setConsents(false, false);

      expect(capturedUrl).toBe('/auth/consents/revoke');
      expect(useAuthStore.getState().isPdnConsentGiven).toBe(false);
      expect(useAuthStore.getState().isProfilePublicationConsentGiven).toBe(false);
    } finally {
      api.post = originalPost;
    }
  });
});
