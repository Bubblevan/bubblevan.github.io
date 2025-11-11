import React from 'react';
import type { JSX } from 'react';
import Layout from '@theme/Layout';
import { useLocation } from '@docusaurus/router';

import DocumentMetadata from './DocumentMetadata';
import DynamicSidebar from './DynamicSidebar';
import styles from './CustomDocLayout.module.css';

export interface CustomDocLayoutProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  showMetadata?: boolean;
}

export default function CustomDocLayout({
  title,
  description,
  children,
  showMetadata = true,
}: CustomDocLayoutProps): JSX.Element {
  const location = useLocation();
  const isDocPage = location.pathname.startsWith('/docs/');

  return (
    <Layout title={title} description={description}>
      {showMetadata && <DocumentMetadata />}
      <div className={styles.customDocLayout}>
        {isDocPage && (
          <aside className={styles.customSidebar}>
            <DynamicSidebar />
          </aside>
        )}
        <main className={styles.customContent}>
          {children}
        </main>
      </div>
    </Layout>
  );
}
