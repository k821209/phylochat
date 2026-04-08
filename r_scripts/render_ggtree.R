#!/usr/bin/env Rscript
# PhyloChat default ggtree rendering script
# Usage: Rscript render_ggtree.R <newick_file> <output_file> [options_json]

suppressPackageStartupMessages({
  library(ggtree)
  library(treeio)
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
newick_file <- args[1]
output_file <- args[2]

tree <- read.newick(newick_file)

# Default plot
p <- ggtree(tree) +
  geom_tiplab() +
  theme_tree2()

# Determine format from extension
ext <- tools::file_ext(output_file)
device <- ifelse(ext == "svg", "svg", "png")
dpi <- ifelse(ext == "svg", NA, 300)

ggsave(output_file, plot = p, device = device, width = 10, height = 8, dpi = dpi)
cat("Render complete:", output_file, "\n")
