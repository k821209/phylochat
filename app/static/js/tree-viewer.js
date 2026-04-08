/**
 * D3.js Phylogenetic Tree Viewer
 * Renders a rectangular phylogram from nested JSON data.
 */
const TreeViewer = (() => {
    let svg, g, zoom;
    let currentData = null;
    let treeId = null;

    function init() {
        svg = d3.select('#tree-svg');
        g = svg.append('g');

        zoom = d3.zoom()
            .scaleExtent([0.3, 5])
            .on('zoom', (event) => g.attr('transform', event.transform));
        svg.call(zoom);

        // Re-render on resize
        const observer = new ResizeObserver(() => {
            if (currentData) render(currentData);
        });
        observer.observe(document.getElementById('tree-viewer'));
    }

    function render(data) {
        currentData = data;
        g.selectAll('*').remove();

        const container = document.getElementById('tree-viewer');
        const width = container.clientWidth;
        const containerH = container.clientHeight;

        // Skip if container not visible
        if (width === 0 || containerH === 0) return;

        const root = d3.hierarchy(data);
        const leaves = root.leaves();
        const tipCount = leaves.length;

        // Scale height by tip count: minimum 20px per tip, at least container height
        const minPerTip = 20;
        const neededH = tipCount * minPerTip + 40;
        const height = Math.max(containerH, neededH);

        // Update viewBox and SVG size
        svg.attr('viewBox', [0, 0, width, height]);
        svg.attr('width', width).attr('height', height);

        // Margins
        const margin = { top: 20, right: 200, bottom: 20, left: 30 };
        const innerW = width - margin.left - margin.right;
        const innerH = height - margin.top - margin.bottom;

        // Compute max depth for branch length scaling
        const maxDepth = _maxCumulativeDepth(root);

        // Layout
        const treeLayout = d3.cluster().size([innerH, innerW * 0.6]);
        treeLayout(root);

        // Scale x by branch length if available
        if (maxDepth > 0) {
            _scaleBranchLengths(root, innerW * 0.6, maxDepth);
        }

        // Position the tree group with margins
        g.attr('transform', `translate(${margin.left}, ${margin.top})`);
        // Reset zoom
        svg.call(zoom.transform, d3.zoomIdentity);

        // Draw links (rectangular elbow)
        g.selectAll('.link')
            .data(root.links())
            .join('path')
            .attr('class', 'link')
            .attr('d', d => `M${d.source.y},${d.source.x}V${d.target.x}H${d.target.y}`);

        // Draw nodes
        const node = g.selectAll('.node')
            .data(root.descendants())
            .join('g')
            .attr('class', d => `node ${d.children ? 'node--internal' : 'node--leaf'}`)
            .attr('transform', d => `translate(${d.y},${d.x})`);

        // Internal node circles
        node.filter(d => d.children)
            .append('circle')
            .attr('r', 3);

        // Tip labels
        const fontSize = Math.min(14, Math.max(8, innerH / tipCount * 0.7));
        node.filter(d => !d.children)
            .append('text')
            .attr('dx', 8)
            .attr('dy', 3)
            .attr('font-size', fontSize + 'px')
            .text(d => d.data.name);

        // Bootstrap values on internal nodes
        node.filter(d => d.children && d.data.bootstrap)
            .append('text')
            .attr('dx', -5)
            .attr('dy', -8)
            .attr('text-anchor', 'end')
            .attr('font-size', '9px')
            .attr('fill', '#888')
            .text(d => Math.round(d.data.bootstrap));

        // Hide placeholder, show SVG
        document.getElementById('tree-placeholder').style.display = 'none';
        document.getElementById('tree-svg').style.display = 'block';
    }

    function _maxCumulativeDepth(root) {
        let max = 0;
        root.each(node => {
            let depth = 0;
            let current = node;
            while (current.parent) {
                depth += current.data.branch_length || 0;
                current = current.parent;
            }
            if (depth > max) max = depth;
        });
        return max;
    }

    function _scaleBranchLengths(root, width, maxDepth) {
        root.each(node => {
            let depth = 0;
            let current = node;
            while (current.parent) {
                depth += current.data.branch_length || 0;
                current = current.parent;
            }
            node.y = (depth / maxDepth) * width;
        });
    }

    function setTreeId(id) { treeId = id; }
    function getTreeId() { return treeId; }
    function getData() { return currentData; }

    function resetZoom() {
        svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
    }

    return { init, render, setTreeId, getTreeId, getData, resetZoom };
})();
