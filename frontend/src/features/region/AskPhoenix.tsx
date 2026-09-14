import { Bot, LoaderCircle, MessageCircle, Send, Sparkles, User, X } from "lucide-react";
import axios from "axios";
import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useLocation } from "react-router-dom";

import { askPhoenix } from "../../services/api";

const suggestedQuestions = [
  "Which events are highest risk?",
  "Why was an event classified as a gas flare?",
  "Which facilities have anomalous activity?",
  "How many people are exposed?",
  "What alerts need attention?",
];

type Message = {
  role: "user" | "assistant";
  text: string;
};

function renderInlineMarkdown(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={`${part}-${index}`} className="font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }

    return <span key={`${part}-${index}`}>{part}</span>;
  });
}

function AssistantMessage({ text }: { text: string }) {
  const lines = text.split(/\r?\n/);

  return (
    <div className="max-w-[88%] rounded-xl bg-muted px-4 py-3 text-sm leading-6 text-foreground">
      <div className="space-y-2">
        {lines.map((line, index) => {
          const numberedItem = line.match(/^\s*(\d+)\.\s+(.*)$/);
          const bulletItem = line.match(/^\s*[-*]\s+(.*)$/);
          const heading = line.match(/^\s*#{1,3}\s+(.*)$/);

          if (numberedItem) {
            return (
              <div key={`${line}-${index}`} className="flex gap-2 pl-1">
                <span className="font-medium text-primary">{numberedItem[1]}.</span>
                <span>{renderInlineMarkdown(numberedItem[2])}</span>
              </div>
            );
          }

          if (bulletItem) {
            return (
              <div key={`${line}-${index}`} className="flex gap-2 pl-1">
                <span className="text-primary">•</span>
                <span>{renderInlineMarkdown(bulletItem[1])}</span>
              </div>
            );
          }

          if (heading) {
            return (
              <p key={`${line}-${index}`} className="font-semibold text-foreground">
                {renderInlineMarkdown(heading[1])}
              </p>
            );
          }

          if (!line.trim()) {
            return <div key={`${line}-${index}`} className="h-1" aria-hidden="true" />;
          }

          return (
            <p key={`${line}-${index}`}>
              {renderInlineMarkdown(line)}
            </p>
          );
        })}
      </div>
    </div>
  );
}

export default function AskPhoenix() {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [isOpen]);

  async function submitQuestion(event?: FormEvent) {
    event?.preventDefault();
    const value = question.trim();
    if (!value || isLoading) return;

    setMessages((current) => [...current, { role: "user", text: value }]);
    setQuestion("");
    setError(null);
    setIsLoading(true);

    try {
      const response = await askPhoenix(value);
      setMessages((current) => [
        ...current,
        { role: "assistant", text: response.answer },
      ]);
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        const detail = requestError.response?.data?.detail;

        setError(
          typeof detail === "string"
            ? detail
            : requestError.code === "ERR_NETWORK"
              ? "Ask Phoenix could not reach the backend. Start the API on http://localhost:8000."
              : "Ask Phoenix could not answer right now. Check the backend logs.",
        );
      } else {
        setError("Ask Phoenix could not answer right now. Check the backend logs.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  // Ask Phoenix only appears on region/explore/facilities pages, never on the
  // landing page ("/"). All hooks above still run on every render.
  if (location.pathname === "/") {
    return null;
  }

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-[1200] bg-foreground/10 backdrop-blur-[2px]"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setIsOpen(false);
            }
          }}
        >
          <section
            id="ask-phoenix"
            role="dialog"
            aria-modal="true"
            aria-labelledby="ask-phoenix-title"
            className="absolute bottom-24 right-4 w-[min(420px,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-border bg-card shadow-2xl sm:right-6"
          >
        <div className="border-b border-border bg-gradient-to-r from-card to-accent/30 px-5 py-5 sm:px-7">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 id="ask-phoenix-title" className="mt-1 text-xl font-semibold text-card-foreground">
                Ask Phoenix about Dahej
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Ask about events, facilities, anomalies, risk, exposure, or alerts.
              </p>
            </div>
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              aria-label="Close Ask Phoenix"
              className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-accent hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {messages.length > 0 && (
          <div className="max-h-80 space-y-4 overflow-y-auto p-5 sm:p-7">
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`flex gap-3 ${message.role === "user" ? "justify-end" : ""}`}
              >
                {message.role === "assistant" && (
                  <Bot className="mt-1 h-4 w-4 shrink-0 text-primary" />
                )}
                {message.role === "user" ? (
                  <p className="max-w-[85%] whitespace-pre-wrap rounded-xl bg-primary px-4 py-3 text-sm leading-6 text-primary-foreground">
                    {message.text}
                  </p>
                ) : (
                  <AssistantMessage text={message.text} />
                )}
                {message.role === "user" && (
                  <User className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
                )}
              </div>
            ))}
            {isLoading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <LoaderCircle className="h-4 w-4 animate-spin text-primary" />
                Searching…
              </div>
            )}
          </div>
        )}

        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2 px-5 pt-5 sm:px-7">
            {suggestedQuestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => setQuestion(suggestion)}
                className="rounded-full border border-border bg-background px-3 py-2 text-left text-xs text-muted-foreground transition hover:border-primary/40 hover:text-foreground"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        <form onSubmit={submitQuestion} className="p-5 sm:p-7">
          {error && (
            <p className="mb-3 rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger">
              {error}
            </p>
          )}
          <div className="flex items-center gap-2 rounded-xl border border-input bg-background p-2 shadow-sm transition focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/10">
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about a thermal event or facility…"
              maxLength={600}
              className="min-w-0 flex-1 bg-transparent px-2 text-sm text-foreground outline-none placeholder:text-muted-foreground"
              aria-label="Ask Phoenix a question"
            />
            <button
              type="submit"
              disabled={!question.trim() || isLoading}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Send question"
            >
              {isLoading ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
        </form>
          </section>
        </div>
      )}

      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        aria-expanded={isOpen}
        aria-controls="ask-phoenix"
        aria-label={isOpen ? "Close Ask Phoenix" : "Open Ask Phoenix"}
        className="fixed bottom-5 right-5 z-[1201] flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/25 transition hover:scale-105 hover:bg-primary/90 focus:outline-none focus:ring-4 focus:ring-primary/25 sm:bottom-6 sm:right-6"
      >
        {isOpen ? (
          <X className="h-6 w-6" />
        ) : (
          <MessageCircle className="h-6 w-6" />
        )}
      </button>
    </>
  );
}