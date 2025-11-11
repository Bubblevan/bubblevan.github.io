import React from 'react';
import { useLocation } from '@docusaurus/router';
import CustomDocLayout from './CustomDocLayout';

interface CustomDocPageProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
}

const CustomDocPage: React.FC<CustomDocPageProps> = ({
  children,
  title,
  description
}) => {
  const location = useLocation();

  // 只在文档页面使用自定义布局
  if (location.pathname.startsWith('/docs/')) {
    return (
      <CustomDocLayout title={title} description={description}>
        {children}
      </CustomDocLayout>
    );
  }

  // 其他页面使用默认布局
  return <>{children}</>;
};

export default CustomDocPage;
