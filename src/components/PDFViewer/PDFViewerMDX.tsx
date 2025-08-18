import React from 'react';
import PDFViewer from './PDFViewer';

interface PDFViewerMDXProps {
  src: string;
  title?: string;
  height?: string | number;
  width?: string | number;
  showToolbar?: boolean;
}

const PDFViewerMDX: React.FC<PDFViewerMDXProps> = ({
  src,
  title = 'PDF文档',
  height = '600px',
  width = '100%',
  showToolbar = true,
}) => {
  return (
    <div style={{ margin: '20px 0' }}>
      <PDFViewer
        src={src}
        title={title}
        height={height}
        width={width}
        showToolbar={showToolbar}
      />
    </div>
  );
};

export default PDFViewerMDX; 