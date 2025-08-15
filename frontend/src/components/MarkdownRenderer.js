import React from 'react';
import ReactMarkdown from 'react-markdown';

const MarkdownRenderer = ({ content }) => {
  return (
    <ReactMarkdown
      components={{
        code: ({ node, inline, className, children, ...props }) => {
          return inline ? (
            <code className="inline-code" {...props}>
              {children}
            </code>
          ) : (
            <pre className="code-block">
              <code className={className} {...props}>
                {children}
              </code>
            </pre>
          );
        },
        blockquote: ({ children, ...props }) => (
          <blockquote className="markdown-blockquote" {...props}>
            {children}
          </blockquote>
        ),
        h1: ({ children, ...props }) => (
          <h1 className="markdown-h1" {...props}>
            {children}
          </h1>
        ),
        h2: ({ children, ...props }) => (
          <h2 className="markdown-h2" {...props}>
            {children}
          </h2>
        ),
        h3: ({ children, ...props }) => (
          <h3 className="markdown-h3" {...props}>
            {children}
          </h3>
        ),
        ul: ({ children, ...props }) => (
          <ul className="markdown-ul" {...props}>
            {children}
          </ul>
        ),
        ol: ({ children, ...props }) => (
          <ol className="markdown-ol" {...props}>
            {children}
          </ol>
        ),
        li: ({ children, ...props }) => (
          <li className="markdown-li" {...props}>
            {children}
          </li>
        ),
        p: ({ children, ...props }) => (
          <p className="markdown-p" {...props}>
            {children}
          </p>
        ),
        strong: ({ children, ...props }) => (
          <strong className="markdown-strong" {...props}>
            {children}
          </strong>
        ),
        em: ({ children, ...props }) => (
          <em className="markdown-em" {...props}>
            {children}
          </em>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
};

export default MarkdownRenderer;