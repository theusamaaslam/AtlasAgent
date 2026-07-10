import React, {useState} from 'react';
import clsx from 'clsx';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './index.module.css';

const memoryLayers = {
  curated: {
    index: '01',
    title: 'Curated truth',
    detail: 'USER.md and MEMORY.md hold identity, durable preferences, and the facts Atlas should trust first.',
    result: 'Usama prefers production-ready changes that are tested on the sandbox.',
  },
  summaries: {
    index: '02',
    title: 'Facts + summaries',
    detail: 'Compact LLM summaries and promoted facts are searched with semantic and lexical ranking.',
    result: 'Dashboard work should preserve the Atlas palette and avoid clipped background panels.',
  },
  archive: {
    index: '03',
    title: 'Raw archive',
    detail: 'Full sessions stay searchable as evidence when curated memory cannot answer the current question.',
    result: 'Source: session 86f82d, message 42. Confidence 0.88.',
  },
} as const;

type MemoryLayer = keyof typeof memoryLayers;

const surfaces = [
  ['CLI', 'The fast path for direct work, scripts, and remote machines.'],
  ['TUI', 'A rich terminal interface with the same sessions and tools.'],
  ['Dashboard', 'Chat, memory, models, files, logs, skills, and operations on port 9119.'],
  ['Gateway', 'Keep Atlas available through Telegram, Discord, Slack, and more.'],
];

function MemoryScene() {
  return (
    <div className={styles.scene} aria-label="Atlas memory graph illustration">
      <div className={styles.sceneHeader}>
        <span>live memory</span>
        <span className={styles.liveIndicator}>growing</span>
      </div>
      <div className={styles.sceneCanvas} aria-hidden="true">
        <span className={clsx(styles.edge, styles.edgeOne)} />
        <span className={clsx(styles.edge, styles.edgeTwo)} />
        <span className={clsx(styles.edge, styles.edgeThree)} />
        <span className={clsx(styles.edge, styles.edgeFour)} />
        <span className={clsx(styles.edge, styles.edgeFive)} />
        <span className={clsx(styles.edge, styles.edgeSix)} />
        <span className={clsx(styles.graphNode, styles.nodeAtlas)}>Atlas</span>
        <span className={clsx(styles.graphNode, styles.nodeUser)}>User</span>
        <span className={clsx(styles.graphNode, styles.nodeFact)}>Fact</span>
        <span className={clsx(styles.graphNode, styles.nodeSummary)}>Summary</span>
        <span className={clsx(styles.graphNode, styles.nodeProject)}>Project</span>
        <span className={clsx(styles.graphNode, styles.nodeDecision)}>Decision</span>
        <span className={styles.graphPulse} />
      </div>
      <div className={styles.sceneConsole}>
        <div>
          <span className={styles.prompt}>$</span> atlas memory recall{' '}
          <span className={styles.query}>&quot;what matters here?&quot;</span>
        </div>
        <div className={styles.consoleResult}>
          <span>6 memories ranked</span>
          <span>38ms</span>
        </div>
      </div>
    </div>
  );
}

function RecallLab() {
  const [active, setActive] = useState<MemoryLayer>('summaries');
  const current = memoryLayers[active];

  return (
    <div className={styles.recallLab}>
      <div className={styles.layerTabs} aria-label="Memory recall layers" role="tablist">
        {(Object.keys(memoryLayers) as MemoryLayer[]).map((key) => (
          <button
            aria-selected={active === key}
            className={clsx(styles.layerTab, active === key && styles.layerTabActive)}
            key={key}
            onClick={() => setActive(key)}
            role="tab"
            type="button"
          >
            <span>{memoryLayers[key].index}</span>
            {memoryLayers[key].title}
          </button>
        ))}
      </div>
      <div className={styles.recallResult} role="tabpanel">
        <div className={styles.resultMeta}>
          <span>recall layer {current.index}</span>
          <span>source cited</span>
        </div>
        <h3>{current.title}</h3>
        <p>{current.detail}</p>
        <blockquote>{current.result}</blockquote>
      </div>
    </div>
  );
}

export default function Home(): React.ReactNode {
  const mark = useBaseUrl('/img/favicon.svg');

  return (
    <Layout
      title="Atlas Agent"
      description="Atlas Agent is a self-improving AI agent created by Usama Aslam with evolving memory, skills, tools, and a production dashboard."
    >
      <main className={styles.page}>
        <section className={styles.hero}>
          <div className={styles.heroGrid} aria-hidden="true" />
          <div className={styles.heroInner}>
            <div className={styles.heroCopy}>
              <div className={styles.brandLine}>
                <img alt="" src={mark} />
                <span>Created by Usama Aslam</span>
              </div>
              <h1>Atlas Agent</h1>
              <p className={styles.heroKicker}>An AI agent that gets better at being yours.</p>
              <p className={styles.lede}>
                It remembers the useful parts, turns repeated work into skills, and carries one
                evolving mind across your terminal, dashboard, and messaging apps.
              </p>
              <div className={styles.actions}>
                <Link className={clsx(styles.button, styles.primary)} to="/getting-started/installation">
                  Install Atlas <span aria-hidden="true">-&gt;</span>
                </Link>
                <Link className={clsx(styles.button, styles.secondary)} to="/getting-started/quickstart">
                  Take the quick tour
                </Link>
                <a className={styles.githubLink} href="https://github.com/theusamaaslam/AtlasAgent">
                  View on GitHub
                </a>
              </div>
            </div>
            <MemoryScene />
          </div>
          <div className={styles.scrollCue} aria-hidden="true">
            <span /> keep scrolling
          </div>
        </section>

        <section className={styles.marquee} aria-label="Atlas capabilities">
          <div>
            <span>Persistent memory</span><i /><span>Semantic recall</span><i />
            <span>Agent-made skills</span><i /><span>Real tool execution</span><i />
            <span>Always-on gateway</span>
          </div>
        </section>

        <section className={styles.memoryBand}>
          <div className={styles.bandInner}>
            <div className={styles.sectionIntro}>
              <p className={styles.eyebrow}>Memory that earns its keep</p>
              <h2>Atlas knows where to look before it says it does not know.</h2>
              <p>
                Recall follows a deliberate order. Current instructions win, curated truth comes
                first, compact memory comes next, and the full archive remains available as fallback evidence.
              </p>
            </div>
            <RecallLab />
          </div>
        </section>

        <section className={styles.capabilityBand}>
          <div className={styles.bandInner}>
            <div className={styles.sectionIntro}>
              <p className={styles.eyebrow}>One agent, many doors</p>
              <h2>Start in the terminal. Continue wherever work finds you.</h2>
            </div>
            <div className={styles.surfaceList}>
              {surfaces.map(([title, detail], index) => (
                <article className={styles.surfaceRow} key={title}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <h3>{title}</h3>
                  <p>{detail}</p>
                  <b aria-hidden="true">+</b>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.launchBand}>
          <div className={styles.launchInner}>
            <div>
              <p className={styles.eyebrow}>Ready when you are</p>
              <h2>Give Atlas a machine.<br />It will bring the memory.</h2>
              <p>
                Local, VPS, Docker, SSH, or your own infrastructure. Your data and your model choices stay yours.
              </p>
            </div>
            <div className={styles.installPanel}>
              <div className={styles.installTopline}>
                <span>production path</span><span>4 steps</span>
              </div>
              <ol>
                <li><span>01</span><code>git clone https://github.com/theusamaaslam/AtlasAgent.git</code></li>
                <li><span>02</span><code>cd AtlasAgent &amp;&amp; bash scripts/install.sh</code></li>
                <li><span>03</span><code>atlas setup</code></li>
                <li><span>04</span><code>atlas dashboard --host 0.0.0.0 --port 9119</code></li>
              </ol>
              <Link className={clsx(styles.button, styles.launchButton)} to="/getting-started/installation">
                Open installation guide <span aria-hidden="true">-&gt;</span>
              </Link>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}

