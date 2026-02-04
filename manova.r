# Load necessary libraries
if (!require("readr")) install.packages("readr")
if (!require("dplyr")) install.packages("dplyr")
if (!require("tidyr")) install.packages("tidyr")
if (!require("ggplot2")) install.packages("ggplot2")
if (!require("scales")) install.packages("scales")

library(readr)
library(dplyr)
library(tidyr)
library(ggplot2)
library(scales)

# ==============================================================================
# 1. SETUP PATHS
# ==============================================================================
input_filename <- "efd_normalized_final.csv"

# Optional: Attempt to set working directory to script location
if (interactive() && requireNamespace("rstudioapi", quietly = TRUE)) {
  setwd(dirname(rstudioapi::getActiveDocumentContext()$path))
}

if (!file.exists(input_filename)) {
  stop(paste("Error: The file", input_filename, "was not found in:", getwd()))
}

full_data <- read_csv(input_filename, show_col_types = FALSE)

# ==============================================================================
# 2. HELPER FUNCTION: Calculate Variance % (With Interaction)
# ==============================================================================

calculate_sscp_percent <- function(data_subset) {
  # 1. Prepare Data
  harmonic_cols <- grep("^[abcd][0-9]+$", names(data_subset), value = TRUE)
  harmonic_cols <- setdiff(harmonic_cols, c("a1", "b1", "c1"))
  
  Y <- as.matrix(data_subset[, harmonic_cols])
  
  # 2. Run MANOVA Model with INTERACTION
  mod <- lm(Y ~ species + locality + sex + species:sex, data = data_subset)
  
  # 3. Calculate SSCP
  manova_summary <- summary(manova(mod))
  
  get_trace <- function(term_name) {
    if (term_name %in% names(manova_summary$SS)) {
      return(sum(diag(manova_summary$SS[[term_name]])))
    } else {
      return(0)
    }
  }

  tr_species     <- get_trace("species")
  tr_locality    <- get_trace("locality")
  tr_sex         <- get_trace("sex")
  tr_interaction <- get_trace("species:sex")
  tr_resid       <- get_trace("Residuals")
  
  total_trace <- tr_species + tr_locality + tr_sex + tr_interaction + tr_resid
  
  return(data.frame(
    Term = c("Species", "Locality", "Sex", "Species:Sex Interaction", "Individual Variation"),
    Contribution = c(
      tr_species / total_trace * 100,
      tr_locality / total_trace * 100,
      tr_sex / total_trace * 100,
      tr_interaction / total_trace * 100,
      tr_resid / total_trace * 100
    )
  ))
}

# ==============================================================================
# 3. MAIN EXECUTION LOOP
# ==============================================================================

plot_data_list <- list()
cell_types <- unique(full_data$cell_type)

for (ct in cell_types) {
  cat(paste("Processing Cell Type:", ct, "...\n"))
  
  subset_df <- full_data %>% filter(cell_type == ct)
  
  n_species <- length(unique(subset_df$species))
  n_sex <- length(unique(subset_df$sex))
  
  if (n_species > 1 && n_sex > 1) {
    variance_df <- calculate_sscp_percent(subset_df)
    variance_df$Cell_Type <- ct
    plot_data_list[[ct]] <- variance_df
  } else {
    cat(paste("Skipping interaction for", ct, "- insufficient species/sex diversity.\n"))
  }
}

final_df <- do.call(rbind, plot_data_list)

# ==============================================================================
# 4. PLOTTING (With White Background)
# ==============================================================================

final_df$Term <- factor(final_df$Term, 
                        levels = c("Individual Variation", "Species:Sex Interaction", "Sex", "Locality", "Species"))

my_colors <- c(
  "Species" = "#1b9e77", 
  "Locality" = "#d95f02", 
  "Sex" = "#7570b3", 
  "Species:Sex Interaction" = "#e7298a",
  "Individual Variation" = "#666666"
)

p <- ggplot(final_df, aes(x = Cell_Type, y = Contribution, fill = Term)) +
  geom_bar(stat = "identity", position = "stack", width = 0.6) +
  scale_fill_manual(values = my_colors) + 
  labs(
    title = "Sources of Variation (Including Interaction)",
    subtitle = "Analysis of Variance Components (MANOVA)",
    y = "Variance Explained (%)",
    x = "Cell Type",
    fill = "Factor"
  ) +
  theme_bw(base_size = 14) +  # Changed to theme_bw for a solid box/grid
  theme(
    plot.title = element_text(face = "bold"),
    legend.position = "right",
    # Explicitly force white backgrounds
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA)
  ) +
  geom_text(aes(label = ifelse(Contribution > 1.5, paste0(round(Contribution, 1), "%"), "")), 
            position = position_stack(vjust = 0.5), size = 3.5, color="white", fontface="bold")

# Save (Added bg = "white")
output_filename <- "variance_with_interaction.png"
ggsave(output_filename, plot = p, width = 8, height = 6, dpi = 300, bg = "white")

print(paste("✅ Analysis Complete. Plot saved to:", file.path(getwd(), output_filename)))