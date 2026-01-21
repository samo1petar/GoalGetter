/**
 * BlockNote <-> Markdown Conversion Utilities
 *
 * Provides bidirectional conversion between Markdown (used by AI Coach)
 * and BlockNote JSON (used by the goal editor).
 *
 * Uses BlockNote's built-in methods from the editor instance.
 */

import type { BlockNoteEditor, PartialBlock, Block } from '@blocknote/core';

/**
 * Convert Markdown string to BlockNote blocks.
 * Used when AI Coach writes goal content.
 *
 * @param markdown - The Markdown string to convert
 * @param editor - The BlockNote editor instance (provides schema and parsing)
 * @returns Array of BlockNote blocks
 */
export function markdownToBlocks(
  markdown: string,
  editor: BlockNoteEditor
): Block[] {
  if (!markdown || markdown.trim() === '') {
    return [];
  }

  try {
    // Use the editor's built-in Markdown parser
    const blocks = editor.tryParseMarkdownToBlocks(markdown);
    return blocks;
  } catch (error) {
    console.error('Failed to parse Markdown to blocks:', error);
    // Fallback: create a simple paragraph with the content
    return [
      {
        id: crypto.randomUUID(),
        type: 'paragraph',
        props: {},
        content: [{ type: 'text', text: markdown, styles: {} }],
        children: [],
      } as unknown as Block,
    ];
  }
}

/**
 * Convert BlockNote blocks to Markdown string.
 * Used when AI Coach reads goal content.
 *
 * @param blocks - The BlockNote blocks to convert
 * @param editor - The BlockNote editor instance (provides schema and serialization)
 * @returns Markdown string
 */
export function blocksToMarkdown(
  blocks: PartialBlock[],
  editor: BlockNoteEditor
): string {
  if (!blocks || blocks.length === 0) {
    return '';
  }

  try {
    // Use the editor's built-in Markdown serializer
    // blocksToMarkdownLossy indicates some formatting may be lost
    const markdown = editor.blocksToMarkdownLossy(blocks);
    return markdown;
  } catch (error) {
    console.error('Failed to convert blocks to Markdown:', error);
    // Fallback: use plain text extraction
    return extractPlainText(blocks);
  }
}

/**
 * Parse stored goal content (JSON string) to Markdown.
 * Handles both BlockNote JSON and plain text formats.
 *
 * @param content - The stored content (may be JSON or plain text)
 * @param editor - The BlockNote editor instance (provides schema)
 * @returns Markdown string
 */
export function goalContentToMarkdown(
  content: string,
  editor: BlockNoteEditor
): string {
  if (!content || content.trim() === '') {
    return '';
  }

  try {
    // Try to parse as BlockNote JSON
    const blocks = JSON.parse(content) as PartialBlock[];
    if (Array.isArray(blocks)) {
      return blocksToMarkdown(blocks, editor);
    }
    // Not an array, return as plain text
    return content;
  } catch {
    // Content is already plain text (not valid JSON)
    return content;
  }
}

/**
 * Convert Markdown content to BlockNote JSON string for storage.
 * Used when AI Coach creates/updates goal content.
 *
 * @param markdown - The Markdown string from AI Coach
 * @param editor - The BlockNote editor instance (provides schema)
 * @returns JSON string of BlockNote blocks
 */
export function markdownToGoalContent(
  markdown: string,
  editor: BlockNoteEditor
): string {
  if (!markdown || markdown.trim() === '') {
    return JSON.stringify([]);
  }

  const blocks = markdownToBlocks(markdown, editor);
  return JSON.stringify(blocks);
}

/**
 * Check if a string is valid BlockNote JSON.
 *
 * @param content - The string to check
 * @returns true if content is valid BlockNote JSON array
 */
export function isBlockNoteJson(content: string): boolean {
  if (!content || content.trim() === '') {
    return false;
  }

  try {
    const parsed = JSON.parse(content);
    // Check if it's an array and has BlockNote-like structure
    if (!Array.isArray(parsed)) return false;
    if (parsed.length === 0) return true;
    // Check first element has expected BlockNote properties
    const first = parsed[0];
    return (
      typeof first === 'object' &&
      first !== null &&
      ('type' in first || 'content' in first)
    );
  } catch {
    return false;
  }
}

/**
 * Fallback plain text extraction from BlockNote blocks.
 * Used when Markdown conversion fails.
 *
 * @param blocks - The BlockNote blocks to extract text from
 * @returns Plain text string
 */
export function extractPlainText(blocks: unknown[]): string {
  if (!Array.isArray(blocks)) return '';

  const extractText = (content: unknown): string => {
    if (!content) return '';
    if (typeof content === 'string') return content;
    if (Array.isArray(content)) {
      return content.map(extractText).join('');
    }
    if (typeof content === 'object' && content !== null) {
      const obj = content as Record<string, unknown>;
      if (obj.text && typeof obj.text === 'string') {
        return obj.text;
      }
      if (obj.content) {
        return extractText(obj.content);
      }
    }
    return '';
  };

  return blocks
    .map((block) => {
      if (typeof block === 'object' && block !== null) {
        const b = block as Record<string, unknown>;
        const text = extractText(b.content);
        // Add formatting hints for block-level elements
        if (b.type === 'heading') return `\n${text}\n`;
        if (b.type === 'bulletListItem') return `- ${text}`;
        if (b.type === 'numberedListItem') return `* ${text}`;
        return text;
      }
      return '';
    })
    .filter(Boolean)
    .join('\n');
}

/**
 * Detect if content appears to be Markdown based on common patterns.
 * Useful for determining content format when no explicit flag is provided.
 *
 * @param content - The content string to analyze
 * @returns true if content appears to be Markdown
 */
export function looksLikeMarkdown(content: string): boolean {
  if (!content) return false;

  // Common Markdown patterns
  const markdownPatterns = [
    /^#{1,6}\s+/m,          // Headings: # ## ### etc.
    /\*\*[^*]+\*\*/,        // Bold: **text**
    /^\*[^*]+\*$/m,         // Italic: *text* (at line start/end to avoid matching lists)
    /^[-*+]\s+/m,           // Unordered list
    /^\d+\.\s+/m,           // Ordered list
    /^>\s+/m,               // Blockquote
    /\[.+\]\(.+\)/,         // Links: [text](url)
    /^```/m,                // Code block
  ];

  return markdownPatterns.some((pattern) => pattern.test(content));
}
