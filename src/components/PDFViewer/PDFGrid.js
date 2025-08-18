import React from 'react';
import PDFGridButton from './PDFGridButton';
import styles from './PDFGridButton.module.css';

const PDFGrid = ({ pdfs }) => {
  return (
    <div className={styles.pdfGridContainer}>
      {pdfs.map((pdf, index) => (
        <PDFGridButton
          key={index}
          pdfUrl={pdf.url}
          title={pdf.title}
          thumbnailUrl={pdf.thumbnailUrl}
        />
      ))}
    </div>
  );
};

export default PDFGrid;