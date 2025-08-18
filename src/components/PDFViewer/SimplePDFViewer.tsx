import React from 'react';
import PDFViewer from './PDFViewer';

interface SimplePDFViewerProps {
  src: string;
  title?: string;
  height?: string | number;
}

const SimplePDFViewer: React.FC<SimplePDFViewerProps> = ({
  src,
  title = 'PDF文档',
  height = '600px',
}) => {
  return (
    <PDFViewer
      src={src}
      title={title}
      height={height}
      showToolbar={true}
    />
  );
};

export default SimplePDFViewer; 