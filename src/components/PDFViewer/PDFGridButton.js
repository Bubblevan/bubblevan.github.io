import React from 'react';
import { useHistory } from '@docusaurus/router';
import styles from './PDFGridButton.module.css';

const PDFGridButton = ({ pdfUrl, title, thumbnailUrl }) => {
  const history = useHistory();

  const handleClick = () => {
    history.push(`/pdf-viewer?file=${encodeURIComponent(pdfUrl)}`);
  };

  return (
    <div className={styles.pdfGridButton} onClick={handleClick}>
      <div
        className={styles.thumbnail}
        style={{ backgroundImage: `url(${thumbnailUrl})` }}
      ></div>
      <div className={styles.title}>{title}</div>
    </div>
  );
};

export default PDFGridButton;