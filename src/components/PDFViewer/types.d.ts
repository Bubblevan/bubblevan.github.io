declare module 'pdfjs-dist' {
  export interface PDFDocumentProxy {
    numPages: number;
    getPage(pageNumber: number): Promise<PDFPageProxy>;
  }

  export interface PDFPageProxy {
    getViewport(params: { scale: number }): PDFPageViewport;
    render(params: PDFRenderParams): PDFRenderTask;
  }

  export interface PDFPageViewport {
    width: number;
    height: number;
  }

  export interface PDFRenderParams {
    canvasContext: CanvasRenderingContext2D;
    viewport: PDFPageViewport;
  }

  export interface PDFRenderTask {
    promise: Promise<void>;
  }

  export interface PDFLoadingTask<T> {
    promise: Promise<T>;
  }

  export interface GlobalWorkerOptions {
    workerSrc: string;
  }

  export const GlobalWorkerOptions: GlobalWorkerOptions;
  export const version: string;
  
  export function getDocument(src: string): PDFLoadingTask<PDFDocumentProxy>;
} 