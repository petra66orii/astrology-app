import Link from "next/link";

export default function Home() {
  return (
    <section className="hero pageShell">
      <p className="eyebrow">Natal astrology, handled carefully</p>
      <h1>Your birth chart should never be built on a guessed time.</h1>
      <p className="lede">Create a private, saved natal chart with precise location and timezone handling. If your birth time is unknown, True Sky clearly shows what can—and cannot—be established.</p>
      <div className="actions">
        <Link className="button" href="/register">Create an account</Link>
        <Link className="textLink" href="/login">I already have an account</Link>
      </div>
      <div className="principles" aria-label="Product principles">
        <article><span>01</span><h2>Exact means exact</h2><p>DST gaps and repeated times are resolved explicitly.</p></article>
        <article><span>02</span><h2>Unknown stays unknown</h2><p>No invented noon, rising sign, houses, or fake precision.</p></article>
        <article><span>03</span><h2>Results stay reproducible</h2><p>Every saved chart records its location and calculation version.</p></article>
      </div>
    </section>
  );
}
