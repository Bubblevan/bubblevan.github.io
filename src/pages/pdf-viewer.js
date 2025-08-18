import React from 'react';
import { useLocation } from '@docusaurus/router';
import { FullPagePDFViewer } from '@site/src/components/PDFViewer';

const PDFViewerPage = () => {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const file = params.get('file');

  if (!file) {
    return <div>Error: No PDF file specified.</div>;
  }

  return (
    <FullPagePDFViewer
      src={file}
      pageSpacing={1}
      maxWidth={1000}
    />
  );
};

export default PDFViewerPage;