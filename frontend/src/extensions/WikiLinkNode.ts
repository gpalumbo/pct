/**
 * WikiLink custom Tiptap node — renders [[feature#task]] as inline chips.
 *
 * Markdown round-trip:
 *   - Serialize: writes [[ref]] via addStorage().markdown.serialize
 *   - Parse: custom markdown-it inline rule matches [[...]]
 */

import { Node, mergeAttributes } from '@tiptap/core';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    wikiLink: {
      insertWikiLink: (ref: string) => ReturnType;
    };
  }
}

const WikiLinkNode = Node.create({
  name: 'wikiLink',
  group: 'inline',
  inline: true,
  atom: true,

  addAttributes() {
    return {
      ref: { default: null },
    };
  },

  parseHTML() {
    return [{ tag: 'span[data-type="wikilink"]', getAttrs: (el) => ({ ref: (el as HTMLElement).getAttribute('data-ref') }) }];
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'data-type': 'wikilink',
        'data-ref': node.attrs.ref,
        class: 'wikilink-chip',
      }),
      `[[${node.attrs.ref}]]`,
    ];
  },

  addCommands() {
    return {
      insertWikiLink:
        (ref: string) =>
        ({ commands }) =>
          commands.insertContent({ type: this.name, attrs: { ref } }),
    };
  },

  addStorage() {
    return {
      markdown: {
        serialize(state: { write: (s: string) => void }, node: { attrs: { ref: string } }) {
          state.write(`[[${node.attrs.ref}]]`);
        },
        parse: {
          setup(markdownit: { inline: { ruler: { push: (name: string, fn: (state: MarkdownItInlineState) => boolean) => void } } }) {
            markdownit.inline.ruler.push('wikilink', (state: MarkdownItInlineState) => {
              const src = state.src.slice(state.pos);
              const match = src.match(/^\[\[([^\]]+)\]\]/);
              if (!match) return false;
              if (!state.env.wikilinks) state.env.wikilinks = [];

              if (!state.pending) {
                // silent mode check
              }

              const token = state.push('html_inline', '', 0);
              token.content = `<span data-type="wikilink" data-ref="${match[1]}" class="wikilink-chip">[[${match[1]}]]</span>`;
              state.pos += match[0].length;
              return true;
            });
          },
        },
      },
    };
  },
});

interface MarkdownItInlineState {
  src: string;
  pos: number;
  env: { wikilinks?: string[] };
  pending: string;
  push: (type: string, tag: string, nesting: number) => { content: string };
}

export default WikiLinkNode;
