import React, { useState } from 'react';
import {
  Layers,
  Server,
  Database,
  Cpu,
  Zap,
  ShieldAlert,
  TrendingUp,
  CheckCircle2,
  Info,
  ArrowRight,
  HardDrive,
  Globe,
  Radio,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

/**
 * Returns an appropriate icon component based on the node type.
 */
function getNodeIcon(type) {
  switch (type?.toLowerCase()) {
    case 'client':
      return <Globe size={16} className="node-icon-client" />;
    case 'gateway':
      return <Radio size={16} className="node-icon-gateway" />;
    case 'service':
      return <Server size={16} className="node-icon-service" />;
    case 'cache':
      return <Zap size={16} className="node-icon-cache" />;
    case 'database':
      return <Database size={16} className="node-icon-database" />;
    case 'queue':
      return <Layers size={16} className="node-icon-queue" />;
    case 'external':
      return <HardDrive size={16} className="node-icon-external" />;
    default:
      return <Cpu size={16} className="node-icon-default" />;
  }
}

/**
 * Educational Senior Reference Architecture Blueprint and Visual Gap Report.
 * Renders for supported System Design questions without affecting candidate scores.
 */
export function SystemDesignBlueprint({
  blueprint,
  coveredConcepts = [],
  missedConcepts = [],
}) {
  const [activeTab, setActiveTab] = useState('tradeoffs'); // 'tradeoffs' | 'resilience' | 'scaling'

  if (!blueprint || !blueprint.nodes || blueprint.nodes.length === 0) {
    return null;
  }

  const {
    title,
    description,
    nodes = [],
    edges = [],
    key_tradeoffs = [],
    failure_considerations = [],
    scaling_considerations = [],
  } = blueprint;

  const safeCovered = Array.isArray(coveredConcepts) ? coveredConcepts : [];
  const safeMissed = Array.isArray(missedConcepts) ? missedConcepts : [];

  return (
    <section
      className="system-design-blueprint-card"
      aria-label="System Design Reference Architecture Blueprint"
    >
      {/* Blueprint Header */}
      <div className="blueprint-header">
        <div className="blueprint-header-title-group">
          <div className="blueprint-icon-badge">
            <Layers size={18} className="blueprint-header-icon" />
          </div>
          <div>
            <div className="blueprint-category-tag">Senior Reference Architecture</div>
            <h5 className="blueprint-title">{title || 'System Architecture Blueprint'}</h5>
          </div>
        </div>
        <span className="blueprint-mode-badge" title="Educational Reference Benchmark">
          Architectural Guide
        </span>
      </div>

      {description && (
        <p className="blueprint-summary-text">{description}</p>
      )}

      {/* Visual Component Topology Canvas */}
      <div className="blueprint-topology-section">
        <div className="topology-section-header">
          <span className="topology-section-label">Topology & Data Flow</span>
          <span className="topology-node-count">
            {nodes.length} Components • {edges.length} Connections
          </span>
        </div>

        <div className="blueprint-canvas-wrapper" tabIndex={0} role="region" aria-label="Architecture Topology Diagram">
          <div className="blueprint-node-grid">
            {nodes.map((node) => {
              const isCore = node.is_core !== false;
              return (
                <div
                  key={node.id}
                  className={`architecture-node-card ${node.type ? `node-type-${node.type}` : ''} ${
                    isCore ? 'is-core-node' : 'is-aux-node'
                  }`}
                  data-node-id={node.id}
                >
                  <div className="node-card-header">
                    <span className="node-type-icon">{getNodeIcon(node.type)}</span>
                    <span className="node-type-label">{node.type?.toUpperCase() || 'NODE'}</span>
                    {isCore && <span className="node-core-badge">CORE</span>}
                  </div>
                  <h6 className="node-label">{node.label}</h6>
                  <p className="node-purpose">{node.purpose}</p>
                </div>
              );
            })}
          </div>

          {/* Connection Flows Summary */}
          {edges.length > 0 && (
            <div className="blueprint-edges-flow">
              <span className="edges-flow-title">Directed Interaction Flows:</span>
              <div className="edges-flow-list">
                {edges.map((edge, eIdx) => {
                  const srcNode = nodes.find((n) => n.id === edge.source);
                  const tgtNode = nodes.find((n) => n.id === edge.target);
                  const isAsync = edge.mode === 'async';

                  return (
                    <div
                      key={eIdx}
                      className={`edge-flow-item ${isAsync ? 'is-async-edge' : 'is-sync-edge'}`}
                    >
                      <span className="edge-src-label">
                        {srcNode ? srcNode.label.split('(')[0].trim() : edge.source}
                      </span>
                      <span className="edge-arrow-group">
                        <ArrowRight size={13} className="edge-arrow-icon" />
                        <span className="edge-action-label">
                          {edge.label} {edge.protocol && <code className="edge-protocol">[{edge.protocol}]</code>}
                        </span>
                      </span>
                      <span className="edge-tgt-label">
                        {tgtNode ? tgtNode.label.split('(')[0].trim() : edge.target}
                      </span>
                      <span className={`edge-mode-tag ${isAsync ? 'tag-async' : 'tag-sync'}`}>
                        {isAsync ? 'async' : 'sync'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Concept Mapping & Educational Alignment */}
      {(safeCovered.length > 0 || safeMissed.length > 0) && (
        <div className="blueprint-concept-alignment">
          <div className="alignment-header">
            <span className="alignment-label">Candidate Answer Architectural Alignment</span>
            <span className="alignment-note">Educational Design Context</span>
          </div>

          <div className="alignment-tags-container">
            {safeCovered.map((concept, idx) => (
              <div key={`cov-${idx}`} className="alignment-chip demonstrated">
                <CheckCircle2 size={13} className="chip-icon" />
                <span className="chip-text">{concept}</span>
                <span className="chip-status-tag">Demonstrated</span>
              </div>
            ))}

            {safeMissed.map((gap, idx) => (
              <div key={`mis-${idx}`} className="alignment-chip consideration">
                <Info size={13} className="chip-icon" />
                <span className="chip-text">{gap}</span>
                <span className="chip-status-tag">Reference Consideration</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Senior Architectural Deep-Dive Accordion / Tabs */}
      <div className="blueprint-deep-dive-section">
        <div className="deep-dive-tab-bar" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'tradeoffs'}
            className={`deep-dive-tab-btn ${activeTab === 'tradeoffs' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('tradeoffs')}
          >
            <Zap size={14} /> Key Trade-offs ({key_tradeoffs.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'resilience'}
            className={`deep-dive-tab-btn ${activeTab === 'resilience' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('resilience')}
          >
            <ShieldAlert size={14} /> Failure Modes & Resilience ({failure_considerations.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'scaling'}
            className={`deep-dive-tab-btn ${activeTab === 'scaling' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('scaling')}
          >
            <TrendingUp size={14} /> Scaling & Partitioning ({scaling_considerations.length})
          </button>
        </div>

        <div className="deep-dive-content-pane" role="tabpanel">
          {activeTab === 'tradeoffs' && (
            <div className="deep-dive-list">
              {key_tradeoffs.length > 0 ? (
                key_tradeoffs.map((item, idx) => (
                  <div key={idx} className="deep-dive-item tradeoff-item">
                    <div className="item-bullet"></div>
                    <p className="item-text">{item}</p>
                  </div>
                ))
              ) : (
                <p className="deep-dive-empty">No trade-off notes specified for this scenario.</p>
              )}
            </div>
          )}

          {activeTab === 'resilience' && (
            <div className="deep-dive-list">
              {failure_considerations.length > 0 ? (
                failure_considerations.map((item, idx) => (
                  <div key={idx} className="deep-dive-item resilience-item">
                    <div className="item-bullet"></div>
                    <p className="item-text">{item}</p>
                  </div>
                ))
              ) : (
                <p className="deep-dive-empty">No failure resilience notes specified for this scenario.</p>
              )}
            </div>
          )}

          {activeTab === 'scaling' && (
            <div className="deep-dive-list">
              {scaling_considerations.length > 0 ? (
                scaling_considerations.map((item, idx) => (
                  <div key={idx} className="deep-dive-item scaling-item">
                    <div className="item-bullet"></div>
                    <p className="item-text">{item}</p>
                  </div>
                ))
              ) : (
                <p className="deep-dive-empty">No scaling notes specified for this scenario.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default SystemDesignBlueprint;
