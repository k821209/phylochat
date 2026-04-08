# PhyloChat Tree Style Guide

Style guidelines for phylogenetic tree visualization using ggtree.
This document defines the default rules PhyloChat follows when generating R code.

---

## 1. Code Structure

Every generated R script follows this skeleton:

```r
library(ggtree)
library(ggplot2)
library(treeio)

tree <- read.newick("path/to/tree.treefile")

p <- ggtree(tree, layout = "rectangular") +
  geom_tiplab(...) +
  geom_text2(...) +    # bootstrap values
  theme_tree2() +
  xlim(0, X)

ggsave("output.png", plot = p, width = W, height = H, dpi = 300)
```

---

## 2. Tip Labels

### Rules
- **Right-align (`align = TRUE`)**: Tip labels are always right-aligned for readability.
- **Dotted leader lines**: A dotted line (`linetype = "dotted"`) connects each tree tip to its label.
- **Offset**: A small gap (`offset = 0.01`) separates the leader line from the label text.

### Defaults
| Parameter | Value     | Description                          |
|-----------|-----------|--------------------------------------|
| size      | 3.5       | Font size                            |
| align     | TRUE      | Right-align labels                   |
| linesize  | 0.3       | Leader line thickness                |
| linetype  | "dotted"  | Leader line style                    |
| offset    | 0.01      | Gap between leader line and label    |

### Code
```r
geom_tiplab(size = 3.5, align = TRUE, linesize = 0.3, linetype = "dotted",
            offset = 0.01)
```

---

## 3. Bootstrap Values

### Rules
- **Placed to the left of the node**: Bootstrap values are positioned at the **upper-left** of each internal node (`hjust > 1`, `vjust < 0`). This prevents overlap with right-aligned tip labels.
- **Threshold filtering**: Only values **>= 70** are displayed by default. Values below 70 indicate weak statistical support and are omitted.
- **Color contrast**: Displayed in **red** to distinguish them from black tree branches.

### Defaults
| Parameter | Value   | Description                            |
|-----------|---------|----------------------------------------|
| size      | 2.5     | Font size (smaller than tip labels)    |
| color     | "red"   | Red to contrast with branches          |
| hjust     | 1.1     | Placed to the left of the node         |
| vjust     | -0.4    | Shifted slightly above the branch      |
| threshold | >= 70   | Minimum value to display               |

### Code
```r
geom_text2(aes(label = label, subset = !isTip & as.numeric(label) >= 70),
           size = 2.5, color = "red", hjust = 1.1, vjust = -0.4)
```

### Threshold Reference
| Threshold | Use Case                                          |
|-----------|---------------------------------------------------|
| >= 50     | Exploratory analysis; inspect all support values   |
| >= 70     | **Default**. Standard for most publications        |
| >= 80     | Show only well-supported nodes                     |
| >= 95     | Very conservative; only strongly supported nodes   |

---

## 4. Layout

### Default: rectangular
```r
ggtree(tree, layout = "rectangular")
```

### Layout Selection Guide
| Layout      | When to Use                                      |
|-------------|--------------------------------------------------|
| rectangular | **Default**. Suitable for most phylogenetic trees |
| circular    | Trees with 50+ tips where space is limited        |
| fan         | Circular layout using only a partial arc          |
| equal_angle | Unrooted tree visualization                       |

---

## 5. Figure Dimensions

### Size Guide by Tip Count (Screen / Digital)
| Tip Count | width | height | Notes                              |
|-----------|-------|--------|------------------------------------|
| < 20      | 10    | 8      | Small tree                         |
| 20 - 50   | 12    | 16     | Medium tree                        |
| 50 - 100  | 16    | 24     | Large tree (e.g., ~70 tips)        |
| > 100     | 16    | 32+    | Very large tree; consider circular |

For print-ready sizing targeting specific paper formats, see **Section 9**.

### Rules
- **Height scales with tip count**: Allocate approximately 0.3 - 0.4 inches per tip.
- **Width depends on branch length and label length**.
- **dpi = 300**: Default resolution for publication-quality output.
- **xlim**: Set generously to prevent label clipping.

---

## 6. Theme

### Default Theme
```r
theme_tree2()   # includes x-axis scale bar
```

| Theme        | Description                                       |
|--------------|---------------------------------------------------|
| theme_tree() | Clean tree with no axes                           |
| theme_tree2()| **Default**. Includes branch length scale on x-axis |

---

## 7. Overlap Prevention Strategy

Label overlap is the most common issue in phylogenetic tree visualization. Apply the following principles in order:

1. **Spatial separation**: Physically separate tip labels (right-aligned) from bootstrap values (left of node).
2. **Dotted leader lines**: Use `align = TRUE` + `linetype = "dotted"` to push tip labels to the right, freeing space near internal nodes.
3. **Threshold filtering**: Display only meaningful bootstrap values (>= 70) to reduce clutter.
4. **Size hierarchy**: Keep bootstrap font size smaller than tip label size to establish visual hierarchy.
5. **Scale figure dimensions**: Ensure sufficient height for the number of tips to prevent vertical crowding.

---

## 8. Default Template

```r
library(ggtree)
library(ggplot2)
library(treeio)

tree <- read.newick("INPUT_PATH")

p <- ggtree(tree, layout = "rectangular") +
  # Tip labels: right-aligned with dotted leader lines
  geom_tiplab(size = 3.5, align = TRUE, linesize = 0.3, linetype = "dotted",
              offset = 0.01) +
  # Bootstrap values: upper-left of node, >= 70 only
  geom_text2(aes(label = label, subset = !isTip & as.numeric(label) >= 70),
             size = 2.5, color = "red", hjust = 1.1, vjust = -0.4) +
  theme_tree2() +
  xlim(0, 2.0)

ggsave("OUTPUT_PATH", plot = p, width = 16, height = 24, dpi = 300)
```

---

## 9. Print-Ready Figure Sizing

Screen-optimized dimensions (Section 5) do not translate directly to print. A figure
that looks reasonable on screen will appear too large, with oversized fonts and thick
lines, when placed into a journal layout or printed at 300 dpi. This section provides
target dimensions and parameter values derived from the physical constraints of common
print formats.

### 9.1 Paper Format Reference Table

Physical dimensions assume standard typeset margins. "Usable width" is the column or
half-page width available to the figure after margins are subtracted.

| Format              | Usable width (in) | Usable height (in) | Typical use case                        |
|---------------------|-------------------|--------------------|-----------------------------------------|
| A4 half-page (H)    | 8.0               | 5.8                | Supplementary figure, single-panel main |
| A4 half-page (V)    | 4.0               | 11.0               | Tall tree with many tips (100+)         |
| A4 full-page        | 8.0               | 11.0               | Full-page figure or plate               |
| Letter half-page    | 7.5               | 5.5                | US journal supplementary figure         |
| Two-column journal  | 3.5               | 3.5 – 5.0          | Inline figure fitting one journal column|

All formats target **dpi = 300** for print output.

### 9.2 Parameter Scaling by Print Size

The values below were validated for a tree with approximately 70 tips. Scale tip label
size proportionally when tip count differs significantly (see note after the table).

| Parameter              | A4 half-page (H) | A4 half-page (V) | A4 full-page   | Letter half-page | Two-column journal |
|------------------------|-------------------|-------------------|----------------|------------------|--------------------|
| **Figure width (in)**  | 8.0               | 4.0               | 8.0            | 7.5              | 3.5                |
| **Figure height (in)** | 5.8               | 11.0              | 11.0           | 5.5              | 3.5 – 5.0          |
| **dpi**                | 300               | 300               | 300            | 300              | 300                |
| **Tip label size**     | 1.8               | 1.2               | 2.8            | 1.7              | 1.2                |
| **Bootstrap size**     | 1.3               | 1.0               | 2.0            | 1.2              | 0.9                |
| **Tip point size**     | 0.8               | 0.6               | 1.2            | 0.8              | 0.5                |
| **Branch line size**   | 0.3               | 0.2               | 0.4            | 0.3              | 0.25               |
| **Leader line size**   | 0.2               | 0.15              | 0.3            | 0.2              | 0.15               |
| **Legend text (pt)**   | 6                 | 5                 | 8              | 6                | 5                  |
| **Legend title (pt)**  | 7 bold            | 6 bold            | 9 bold         | 7 bold           | 6 bold             |
| **Legend key size**    | 0.3 cm            | 0.25 cm           | 0.4 cm         | 0.3 cm           | 0.25 cm            |
| **Axis text (pt)**     | 5                 | 4                 | 7              | 5                | 4                  |
| **Margins (mm)**       | 2 all sides       | 2 all sides       | 3 all sides    | 2 all sides      | 1.5 all sides      |

> **Tip-count adjustment**: The values above assume ~70 tips. For significantly fewer
> tips (< 30), increase tip label size by ~0.3 – 0.5 units. For > 100 tips, decrease
> by ~0.3 units or switch to a circular layout.

### 9.3 A4 Half-Page Template (~70 tips)

This is the reference configuration from which the table above was derived.

```r
library(ggtree)
library(ggplot2)
library(treeio)

tree <- read.newick("INPUT_PATH")

p <- ggtree(tree, layout = "rectangular", size = 0.3) +
  # Tip labels: compact for print
  geom_tiplab(size = 1.8, align = TRUE, linesize = 0.2, linetype = "dotted",
              offset = 0.01) +
  # Bootstrap values: >= 70, sized for print
  geom_text2(aes(label = label, subset = !isTip & as.numeric(label) >= 70),
             size = 1.3, color = "red", hjust = 1.1, vjust = -0.4) +
  theme_tree2() +
  # xlim: tight — just enough to accommodate aligned labels without excess whitespace
  xlim(0, 1.4) +
  theme(
    axis.text.x  = element_text(size = 5),
    legend.text  = element_text(size = 6),
    legend.title = element_text(size = 7, face = "bold"),
    legend.key.size  = unit(0.3, "cm"),
    legend.background = element_rect(fill = alpha("white", 0.7), color = NA),
    plot.margin  = unit(c(2, 2, 2, 2), "mm")
  )

ggsave("OUTPUT_PATH", plot = p, width = 8.0, height = 5.8, dpi = 300)
```

### 9.4 A4 Vertical-Half Template (~140 tips)

A4 portrait page split vertically in half. The tall, narrow shape accommodates trees
with 100+ tips while fitting side-by-side with text or a second panel.

```r
library(ggtree)
library(ggplot2)
library(treeio)

tree <- read.newick("INPUT_PATH")

# Optional: attach metadata for query highlighting
tip_df <- data.frame(
  label = tree$tip.label,
  is_query = ifelse(tree$tip.label == "query", "Query", "Other"),
  stringsAsFactors = FALSE
)

p <- ggtree(tree, layout = "rectangular", size = 0.2) %<+% tip_df +
  # Tip labels: compact, query highlighted in red
  geom_tiplab(aes(color = is_query),
              size = 1.2, align = TRUE, linesize = 0.15, linetype = "dotted",
              offset = 0.001) +
  # Query marker (diamond)
  geom_point2(aes(subset = (isTip & label == "query")),
              color = "#E41A1C", size = 1.5, shape = 18) +
  # Bootstrap values (UFboot >= 70): extract value after "/"
  geom_text2(aes(label = sapply(strsplit(label, "/"), function(x) x[length(x)]),
                 subset = !isTip & !is.na(label) &
                   as.numeric(sapply(strsplit(label, "/"), function(x) x[length(x)])) >= 70),
             size = 1.0, color = "#0072B2", hjust = 1.1, vjust = -0.4) +
  scale_color_manual(values = c("Query" = "#E41A1C", "Other" = "black"), guide = "none") +
  theme_tree2() +
  xlim(0, 0.25) +
  theme(
    axis.text.x  = element_text(size = 4),
    legend.text  = element_text(size = 5),
    legend.title = element_text(size = 6, face = "bold"),
    legend.key.size  = unit(0.25, "cm"),
    legend.background = element_rect(fill = alpha("white", 0.7), color = NA),
    plot.margin  = unit(c(2, 2, 2, 2), "mm")
  )

ggsave("OUTPUT_PATH", plot = p, width = 4.0, height = 11.0, dpi = 300)
```

> **Note on SH-aLRT/UFboot labels**: When the tree file contains composite support
> values (e.g., `"87.7/90"`), extract the UFboot portion with
> `sapply(strsplit(label, "/"), function(x) x[length(x)])` before filtering.

---

### 9.5 xlim Guidance for Print Figures

On-screen figures can afford a generous xlim to prevent clipping. For print figures,
excess horizontal whitespace wastes column space. Set xlim as follows:

1. Run the tree without xlim to inspect the natural branch-length range.
2. Add approximately 20 – 30 % of the x range to accommodate aligned labels.
3. Verify that no tip label is clipped at the right edge.
4. Tighten further if whitespace remains visible after rendered preview.

---

## 10. Query Tip Highlighting

When a tree contains a user-submitted sequence (typically labelled `query`), highlight
it so it stands out from reference sequences.

### 10.1 Recommended Pattern

```r
# 1. Attach metadata via %<+%
tip_df <- data.frame(
  label = tree$tip.label,
  is_query = ifelse(tree$tip.label == "query", "Query", "Other"),
  stringsAsFactors = FALSE
)

p <- ggtree(tree) %<+% tip_df +
  # 2. Color tip label by query status
  geom_tiplab(aes(color = is_query), ...) +
  # 3. Add marker point on query tip
  geom_point2(aes(subset = (isTip & label == "query")),
              color = "#E41A1C", size = 1.5, shape = 18) +
  scale_color_manual(values = c("Query" = "#E41A1C", "Other" = "black"),
                     guide = "none")
```

### 10.2 Common Pitfalls

| Problem | Cause | Solution |
|---------|-------|----------|
| `object 'query' not found` | Using `geom_tippoint(aes(subset = (label == "query")))` — `geom_tippoint` does not reliably resolve `label` in all ggtree versions | **Use `geom_point2`** instead of `geom_tippoint`. `geom_point2` operates on the full tree data (tips + internal nodes), so always add `isTip &` to the subset condition. |
| Custom column not found in subset | `%<+%` join columns (e.g., `is_query`) are available in `geom_tiplab` but may not resolve inside `geom_tippoint` `aes(subset = ...)` | Reference only built-in columns (`label`, `isTip`, `node`) in `geom_point2` subset expressions. Use custom columns only in `geom_tiplab` aesthetics. |
| Query marker overlaps bootstrap text | Both placed near internal nodes | Query marker targets `isTip` nodes only, so no overlap with bootstrap labels on internal nodes. |

### 10.3 Defaults

| Parameter       | Value       | Description                          |
|-----------------|-------------|--------------------------------------|
| Label color     | `#E41A1C`   | Red — same as marker for consistency |
| Marker shape    | 18          | Diamond (◆)                          |
| Marker size     | 1.5         | Visible but not dominant             |
| Marker color    | `#E41A1C`   | Red                                  |
| Other tip color | `black`     | Default for non-query tips           |
| Legend           | `guide = "none"` | Suppress auto-legend for color  |

---

## Changelog

| Date       | Description                                                                                      |
|------------|--------------------------------------------------------------------------------------------------|
| 2026-04-08 | Add §10 Query Tip Highlighting — pattern, pitfalls (geom_tippoint vs geom_point2), defaults.     |
| 2026-04-08 | Add §9.4 A4 Vertical-Half template; add A4 half-page (V) to format & parameter tables.          |
| 2026-04-08 | Add Section 9 (Print-Ready Figure Sizing). Update Section 5 heading and cross-reference to §9.  |
| 2026-04-07 | Initial draft. Define default style guidelines.                                                  |
