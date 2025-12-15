import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { etymologyService, WordFamily, EtymologyNode } from '../../services/etymology';

// Language colors
const LANG_COLORS: Record<string, string> = {
  ru: '#ef4444', // Red for Russian
  en: '#3b82f6', // Blue for English
  de: '#eab308', // Yellow for German
  la: '#8b5cf6', // Purple for Latin
  grc: '#10b981', // Emerald for Greek
  pie: '#64748b', // Slate for Proto-Indo-European (root)
  sla: '#f97316', // Orange for Proto-Slavic
};

export const EtymologyGraph: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<EtymologyNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<EtymologyNode | null>(null);
  const [graphData, setGraphData] = useState<WordFamily | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;
    
    setLoading(true);
    try {
      const results = await etymologyService.searchNodes(searchTerm);
      setSearchResults(results);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadGraph = async (node: EtymologyNode) => {
    setLoading(true);
    setSelectedNode(node);
    try {
      const data = await etymologyService.getWordFamily(node.id);
      setGraphData(data);
      setSearchResults([]); // Clear search results to show graph
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!graphData || !svgRef.current) return;

    const width = 800;
    const height = 600;
    const svg = d3.select(svgRef.current);
    
    // Clear previous graph
    svg.selectAll("*").remove();

    // Simulation setup
    const simulation = d3.forceSimulation(graphData.nodes as any)
      .force("link", d3.forceLink(graphData.edges).id((d: any) => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));

    // Draw lines for edges
    const link = svg.append("g")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(graphData.edges)
      .join("line")
      .attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrowhead)");

    // Arrowhead marker
    svg.append("defs").append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#999");

    // Draw nodes
    const node = svg.append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .selectAll("g")
      .data(graphData.nodes)
      .join("g")
      .call(d3.drag<any, any>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended) as any);

    // Node circles
    node.append("circle")
      .attr("r", 8)
      .attr("fill", (d) => LANG_COLORS[d.language] || '#9ca3af');

    // Node labels
    node.append("text")
      .attr("x", 12)
      .attr("y", 4)
      .text((d) => d.word + (d.is_reconstructed === 'Y' ? '*' : ''))
      .attr("stroke", "none")
      .attr("fill", "#333")
      .attr("font-size", "12px")
      .style("pointer-events", "none");
      
    // Language labels (smaller)
    node.append("text")
      .attr("x", 12)
      .attr("y", 16)
      .text((d) => d.language)
      .attr("stroke", "none")
      .attr("fill", "#666")
      .attr("font-size", "10px")
      .style("pointer-events", "none");

    // Update positions on tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node
        .attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [graphData]);

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="mb-6 flex gap-4">
        <div className="flex-1">
          <h2 className="text-2xl font-bold mb-2">Etymology Graph</h2>
          <p className="text-gray-600 text-sm">Discover connections between words across languages.</p>
        </div>
        <form onSubmit={handleSearch} className="flex gap-2 items-start pt-1">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search word..."
            className="p-2 border border-gray-300 rounded w-64"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-primary-600 text-white px-4 py-2 rounded"
          >
            Search
          </button>
        </form>
      </div>

      {searchResults.length > 0 && (
        <div className="mb-6 bg-white shadow rounded-lg p-4">
          <h3 className="font-bold mb-2">Select a starting node:</h3>
          <ul className="divide-y divide-gray-100">
            {searchResults.map((node) => (
              <li 
                key={node.id} 
                className="py-2 px-3 hover:bg-gray-50 cursor-pointer rounded flex justify-between items-center"
                onClick={() => loadGraph(node)}
              >
                <div>
                  <span className="font-medium">{node.word}</span>
                  <span className="text-gray-500 text-sm ml-2">({node.language})</span>
                </div>
                {node.meaning && <span className="text-gray-400 text-sm">{node.meaning}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="bg-white shadow rounded-lg p-4 h-[650px] flex flex-col">
        {selectedNode && (
            <div className="mb-2 text-sm text-gray-500 border-b pb-2">
                Showing connections for: <span className="font-bold text-gray-900">{selectedNode.word}</span> ({selectedNode.language})
            </div>
        )}
        <div className="flex-1 border border-gray-100 rounded bg-gray-50 relative overflow-hidden">
            {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-white/50 z-10">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                </div>
            )}
            <svg ref={svgRef} width="100%" height="100%" viewBox="0 0 800 600"></svg>
            
            <div className="absolute bottom-4 right-4 bg-white/90 p-2 rounded shadow text-xs">
                <div className="font-bold mb-1">Legend</div>
                {Object.entries(LANG_COLORS).map(([lang, color]) => (
                    <div key={lang} className="flex items-center gap-2 mb-1">
                        <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }}></span>
                        <span className="uppercase">{lang}</span>
                    </div>
                ))}
            </div>
        </div>
      </div>
    </div>
  );
};

