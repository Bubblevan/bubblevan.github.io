import React from 'react';
import type { JSX } from 'react';
import Layout from '@theme/Layout';

import DocumentMetadata from '@site/src/components/DocumentMetadata';

export interface DocumentLayoutProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  showMetadata?: boolean;
}

export default function DocumentLayout({
  title,
  description,
  children,
  showMetadata = true,
}: DocumentLayoutProps): JSX.Element {
  return (
    <Layout title={title} description={description}>
      {showMetadata && <DocumentMetadata />}
      {children}
    </Layout>
  );
}
