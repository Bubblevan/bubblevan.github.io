import React, { useEffect, useState } from 'react';
import styles from './styles.module.css';
import BrowserOnly from '@docusaurus/BrowserOnly';

export interface LinkPreviewData {
  title?: string;
  description?: string;
  image?: string;
  siteName?: string;
  url?: string;
}

export interface LinkPreviewCardProps {
  /**
   * 链接地址
   */
  href: string;
  /**
   * 标题（可选，如果不提供会尝试从链接获取）
   */
  title?: string;
  /**
   * 描述（可选，如果不提供会尝试从链接获取）
   */
  description?: string;
  /**
   * 预览图片（可选，如果不提供会尝试从链接获取）
   */
  image?: string;
  /**
   * 网站名称（可选）
   */
  siteName?: string;
  /**
   * 是否自动获取预览信息
   * @default true
   */
  autoFetch?: boolean;
  /**
   * 自定义样式类名
   */
  className?: string;
}

interface PreviewState {
  title: string;
  description: string;
  image: string;
  siteName: string;
  loading: boolean;
  error: boolean;
}

/**
 * 链接预览卡片组件
 * 
 * 将普通链接渲染为带有预览图片、标题和描述的卡片格式
 * 
 * @example
 * ```tsx
 * <LinkPreviewCard 
 *   href="https://example.com"
 *   title="示例网站"
 *   description="这是一个示例网站"
 *   image="/img/example.jpg"
 * />
 * ```
 */
const LinkPreviewCard: React.FC<LinkPreviewCardProps> = ({
  href,
  title: propTitle,
  description: propDescription,
  image: propImage,
  siteName: propSiteName,
  autoFetch = true,
  className = '',
}) => {
  const [preview, setPreview] = useState<PreviewState>({
    title: propTitle || '',
    description: propDescription || '',
    image: propImage || '',
    siteName: propSiteName || '',
    loading: false,
    error: false,
  });

  // 从 URL 中提取域名作为默认网站名称
  const getDomainName = (url: string): string => {
    try {
      const domain = new URL(url).hostname.replace(/^www\./, '');
      return domain;
    } catch {
      return '';
    }
  };

  // 获取链接预览信息（使用多个 API 服务，提高成功率）
  const fetchPreview = async (url: string) => {
    // 如果已经手动提供了所有信息，不自动获取
    if (!autoFetch || (propTitle && propImage && propDescription)) return;

    setPreview((prev) => ({ ...prev, loading: true, error: false }));

    // 尝试多个 API 服务
    const apis = [
      // API 1: Microlink API (免费，无需 key)
      `https://api.microlink.io?url=${encodeURIComponent(url)}`,
      // API 2: JSONLink API (免费，无需 key)
      `https://api.jsonlink.io/api/extract?url=${encodeURIComponent(url)}`,
      // API 3: LinkPreview API (使用 demo key，如需更多请求请自行申请)
      `https://api.linkpreview.net/?key=demo&q=${encodeURIComponent(url)}`,
    ];

    for (const apiUrl of apis) {
      try {
        const response = await fetch(apiUrl, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          
          // Microlink API 格式
          if (data.data) {
            const result = data.data;
            setPreview({
              title: result.title || propTitle || '',
              description: result.description || propDescription || '',
              image: result.image?.url || result.image || propImage || '',
              siteName: result.publisher || result.siteName || propSiteName || getDomainName(url),
              loading: false,
              error: false,
            });
            return;
          }
          
          // JSONLink API 格式
          if (data.images && data.images.length > 0) {
            setPreview({
              title: data.title || propTitle || '',
              description: data.description || propDescription || '',
              image: data.images[0] || propImage || '',
              siteName: data.site || propSiteName || getDomainName(url),
              loading: false,
              error: false,
            });
            return;
          }
          
          // LinkPreview API 格式
          if (data.title) {
            setPreview({
              title: data.title || propTitle || '',
              description: data.description || propDescription || '',
              image: data.image || propImage || '',
              siteName: data.site_name || propSiteName || getDomainName(url),
              loading: false,
              error: false,
            });
            return;
          }
        }
      } catch (error) {
        // 继续尝试下一个 API
        continue;
      }
    }

    // 所有 API 都失败，使用手动传入的值或默认值
    setPreview({
      title: propTitle || getDomainName(url) || '链接预览',
      description: propDescription || '',
      image: propImage || '',
      siteName: propSiteName || getDomainName(url),
      loading: false,
      error: true,
    });
  };

  useEffect(() => {
    // 如果手动提供了图片，优先使用，但仍可以自动获取其他信息
    if (autoFetch && !propImage) {
      // 如果没有手动提供图片，尝试自动获取
      fetchPreview(href);
    } else if (autoFetch && propImage && (!propTitle || !propDescription)) {
      // 如果有图片但没有标题或描述，仍尝试获取
      fetchPreview(href);
    } else {
      // 使用手动传入的值
      setPreview({
        title: propTitle || getDomainName(href) || '链接预览',
        description: propDescription || '',
        image: propImage || '',
        siteName: propSiteName || getDomainName(href),
        loading: false,
        error: false,
      });
    }
  }, [href, autoFetch, propTitle, propDescription, propImage, propSiteName]);

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    window.open(href, '_blank', 'noopener,noreferrer');
  };

  return (
    <BrowserOnly fallback={<div>Loading...</div>}>
      {() => (
        <a
          href={href}
          onClick={handleClick}
          className={`${styles.linkPreviewCard} ${className}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <div className={styles.imageContainer}>
            {preview.image ? (
              <img
                src={preview.image}
                alt={preview.title}
                className={styles.image}
                onError={(e) => {
                  // 图片加载失败时显示占位图
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  const container = target.parentElement;
                  if (container && !container.querySelector('.placeholder')) {
                    const placeholder = document.createElement('div');
                    placeholder.className = styles.placeholder;
                    placeholder.textContent = preview.siteName || '📄';
                    container.appendChild(placeholder);
                  }
                }}
              />
            ) : (
              <div className={styles.placeholder}>
                {preview.siteName || '📄'}
              </div>
            )}
          </div>
          <div className={styles.content}>
            {preview.siteName && (
              <div className={styles.siteName}>{preview.siteName}</div>
            )}
            <h3 className={styles.title}>{preview.title || href}</h3>
            {preview.description && (
              <p className={styles.description}>{preview.description}</p>
            )}
            <div className={styles.url}>{href}</div>
          </div>
          {preview.loading && (
            <div className={styles.loading}>加载中...</div>
          )}
        </a>
      )}
    </BrowserOnly>
  );
};

export default LinkPreviewCard;
