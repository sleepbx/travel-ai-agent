import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CalendarDays,
  ExternalLink,
  MapPinned,
  Newspaper,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  Ticket,
  TrendingUp,
} from "lucide-react";
import { apiUrl, backendUnavailableMessage } from "../lib/api";
import "./IndiaPulse.css";

const DEFAULT_QUERY = "";

const PULSE_IMAGES = {
  festival: [
    "https://images.unsplash.com/photo-1496372412473-e8548ffd82bc?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1603262110263-fb0112e7cc33?auto=format&fit=crop&w=900&q=80",
  ],
  event: [
    "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=900&q=80",
  ],
  place: [
    "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1477587458883-47145ed94245?auto=format&fit=crop&w=900&q=80",
  ],
  news: [
    "https://images.unsplash.com/photo-1530789253388-582c481c54b0?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80",
  ],
};

function valueText(value, fallback = "") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function sourceImage(title, category) {
  const key = String(category || "").toLowerCase();
  const pool = key.includes("festival")
    ? PULSE_IMAGES.festival
    : key.includes("event")
      ? PULSE_IMAGES.event
      : key.includes("place")
        ? PULSE_IMAGES.place
        : PULSE_IMAGES.news;
  const index = String(title || "india").split("").reduce((sum, char) => sum + char.charCodeAt(0), 0) % pool.length;
  return pool[index];
}

function categoryIcon(category) {
  const text = String(category || "").toLowerCase();
  if (text.includes("event")) return <Ticket size={17} />;
  if (text.includes("festival")) return <Sparkles size={17} />;
  if (text.includes("place")) return <MapPinned size={17} />;
  return <Newspaper size={17} />;
}

function PulseCard({ item }) {
  const fallbackImage = sourceImage(item.title, item.category);
  const image = item.image || fallbackImage;
  const hasLink = Boolean(item.link);

  return (
    <article className="pulse-card">
      <div className="pulse-image">
        <img
          src={image}
          alt=""
          loading="lazy"
          onError={(event) => {
            if (event.currentTarget.src !== fallbackImage) {
              event.currentTarget.src = fallbackImage;
            }
          }}
        />
        <span>{categoryIcon(item.category)} {valueText(item.category, "Travel")}</span>
      </div>
      <div className="pulse-body">
        <div className="pulse-meta">
          <span>{valueText(item.source, "Source")}</span>
          <span>{valueText(item.freshness, "Latest")}</span>
        </div>
        <h3>{valueText(item.title, "India travel update")}</h3>
        <p>{valueText(item.summary, "Open the source for more details.")}</p>
        {hasLink ? (
          <a href={item.link} target="_blank" rel="noreferrer">
            Open source
            <ExternalLink size={15} />
          </a>
        ) : (
          <span className="source-disabled">Live source unavailable</span>
        )}
      </div>
    </article>
  );
}

export default function IndiaPulse() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const loadPulse = useCallback(async (nextQuery = DEFAULT_QUERY) => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({ limit: "9" });
      if (nextQuery.trim()) params.set("q", nextQuery.trim());
      const res = await fetch(apiUrl(`/trends/india?${params.toString()}`));

      if (!res.ok) throw new Error("Could not load India trends");
      const loaded = await res.json();
      setData(loaded);
    } catch (err) {
      setError(err instanceof TypeError ? backendUnavailableMessage() : err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPulse(DEFAULT_QUERY);
  }, [loadPulse]);

  const items = useMemo(() => (Array.isArray(data?.items) ? data.items : []), [data]);
  const suggestions = data?.suggested_queries || [
    "music festivals in India this weekend",
    "trending places near Mumbai",
    "food festivals in India",
  ];

  const submitQuery = (event) => {
    event.preventDefault();
    const nextQuery = draft.trim();
    setQuery(nextQuery);
    loadPulse(nextQuery);
  };

  const runSuggestion = (suggestion) => {
    setDraft(suggestion);
    setQuery(suggestion);
    loadPulse(suggestion);
  };

  return (
    <div className="india-pulse page-wrap">
      <section className="pulse-hero">
        <div>
          <span className="eyebrow dark"><TrendingUp size={16} /> India Pulse</span>
          <h1>Latest travel buzz, events, and trending places in India.</h1>
          <p>
            Live search powers this feed when keys are configured. Without live sources, TravelAI marks fallback
            suggestions clearly so users know what needs verification.
          </p>
        </div>
        <div className="pulse-status">
          <CalendarDays size={24} />
          <span>Updated</span>
          <strong>{valueText(data?.generated_at, "Today")}</strong>
          <p>{valueText(data?.provider, "TravelAI")} - {valueText(data?.status, "ready")}</p>
        </div>
      </section>

      <section className="pulse-layout">
        <div className="pulse-feed">
          <div className="pulse-feed-title">
            <div>
              <span>{query ? "Search results" : "Trending now"}</span>
              <h2>{query || "India travel and event radar"}</h2>
            </div>
            <button onClick={() => loadPulse(query)} disabled={loading}>
              <RefreshCw size={17} />
              Refresh
            </button>
          </div>

          {error && <div className="pulse-error">{error}</div>}

          {loading ? (
            <div className="pulse-grid">
              {[1, 2, 3, 4, 5, 6].map((item) => (
                <div className="pulse-card pulse-skeleton" key={item}></div>
              ))}
            </div>
          ) : (
            <div className="pulse-grid">
              {items.map((item) => (
                <PulseCard item={item} key={item.id || item.title} />
              ))}
            </div>
          )}
        </div>

        <aside className="pulse-query">
          <div className="query-heading">
            <Search size={22} />
            <div>
              <span>Ask the feed</span>
              <h2>Find what is hot</h2>
            </div>
          </div>

          <form onSubmit={submitQuery}>
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Try: events in Delhi this weekend, trending beaches in India, concerts in Bengaluru, best festivals this month..."
              rows={6}
            />
            <button disabled={loading || !draft.trim()}>
              <Send size={17} />
              Search India
            </button>
          </form>

          <div className="query-suggestions">
            <span>Fast searches</span>
            {suggestions.map((suggestion) => (
              <button type="button" onClick={() => runSuggestion(suggestion)} key={suggestion}>
                {suggestion}
              </button>
            ))}
          </div>

          <div className="pulse-note">
            <Newspaper size={18} />
            <p>{valueText(data?.message, "Search India travel news, events, and places.")}</p>
          </div>
        </aside>
      </section>
    </div>
  );
}
