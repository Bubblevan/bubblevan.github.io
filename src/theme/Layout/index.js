import React, {useEffect} from 'react';
import clsx from 'clsx';
import ErrorBoundary from '@docusaurus/ErrorBoundary';
import {
  PageMetadata,
  SkipToContentFallbackId,
  ThemeClassNames,
} from '@docusaurus/theme-common';
import {useKeyboardNavigation} from '@docusaurus/theme-common/internal';
import SkipToContent from '@theme/SkipToContent';
import AnnouncementBar from '@theme/AnnouncementBar';
import Navbar from '@theme/Navbar';
import CustomNavbar from '@site/src/components/CustomNavbar';
import Footer from '@theme/Footer';
import LayoutProvider from '@theme/Layout/Provider';
import ErrorPageContent from '@theme/ErrorPageContent';
import {initStyleDebugger} from '@site/src/utils/styleDebugger';
import styles from './styles.module.css';
export default function Layout(props) {
  const {
    children,
    noFooter,
    wrapperClassName,
    // Not really layout-related, but kept for convenience/retro-compatibility
    title,
    description,
  } = props;
  useKeyboardNavigation();
  
  useEffect(() => {
    initStyleDebugger();
  }, []);
  return (
    <LayoutProvider>
      <PageMetadata title={title} description={description} />

      <SkipToContent />

      <AnnouncementBar />

      <Navbar />
      <CustomNavbar />

      <div
        id={SkipToContentFallbackId}
        className={clsx(
          ThemeClassNames.layout.main.container,
          ThemeClassNames.wrapper.main,
          styles.mainWrapper,
          wrapperClassName,
        )}>
        <ErrorBoundary fallback={(params) => <ErrorPageContent {...params} />}>
          {children}
        </ErrorBoundary>
      </div>

      {!noFooter && <Footer />}
    </LayoutProvider>
  );
}
