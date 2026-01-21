'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import rehypeHighlight from 'rehype-highlight';
import type { Components } from 'react-markdown';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Custom components for rendering markdown elements with appropriate styling.
 * All links open in new tabs with security attributes.
 */
const markdownComponents: Components = {
  // Links open in new tab with security attributes
  a: ({ href, children, ...props }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline hover:text-primary/80 transition-colors"
      {...props}
    >
      {children}
    </a>
  ),
  // Code blocks with syntax highlighting
  pre: ({ children, ...props }) => (
    <pre
      className="bg-muted rounded-md p-3 overflow-x-auto my-2 text-xs"
      {...props}
    >
      {children}
    </pre>
  ),
  // Inline code styling
  code: ({ className, children, ...props }) => {
    // Check if this is a code block (has language class) or inline code
    const isCodeBlock = className?.includes('language-');
    if (isCodeBlock) {
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code
        className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono"
        {...props}
      >
        {children}
      </code>
    );
  },
  // Unordered lists
  ul: ({ children, ...props }) => (
    <ul className="list-disc list-inside my-2 space-y-1" {...props}>
      {children}
    </ul>
  ),
  // Ordered lists
  ol: ({ children, ...props }) => (
    <ol className="list-decimal list-inside my-2 space-y-1" {...props}>
      {children}
    </ol>
  ),
  // List items
  li: ({ children, ...props }) => (
    <li className="text-sm" {...props}>
      {children}
    </li>
  ),
  // Blockquotes
  blockquote: ({ children, ...props }) => (
    <blockquote
      className="border-l-4 border-primary/30 pl-4 my-2 italic text-muted-foreground"
      {...props}
    >
      {children}
    </blockquote>
  ),
  // Headings
  h1: ({ children, ...props }) => (
    <h1 className="text-lg font-bold my-2" {...props}>
      {children}
    </h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 className="text-base font-bold my-2" {...props}>
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 className="text-sm font-bold my-1.5" {...props}>
      {children}
    </h3>
  ),
  // Paragraphs
  p: ({ children, ...props }) => (
    <p className="my-1.5 text-sm leading-relaxed" {...props}>
      {children}
    </p>
  ),
  // Horizontal rule
  hr: ({ ...props }) => (
    <hr className="my-3 border-border" {...props} />
  ),
  // Strong/bold text
  strong: ({ children, ...props }) => (
    <strong className="font-semibold" {...props}>
      {children}
    </strong>
  ),
  // Emphasis/italic text
  em: ({ children, ...props }) => (
    <em className="italic" {...props}>
      {children}
    </em>
  ),
  // Strikethrough (GFM)
  del: ({ children, ...props }) => (
    <del className="line-through text-muted-foreground" {...props}>
      {children}
    </del>
  ),
};

/**
 * MarkdownRenderer component for rendering markdown content in chat messages.
 *
 * Features:
 * - GitHub Flavored Markdown support (tables, strikethrough, autolinks, etc.)
 * - HTML sanitization for XSS protection
 * - Syntax highlighting for code blocks
 * - Consistent styling that matches the application theme
 */
export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize, rehypeHighlight]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
