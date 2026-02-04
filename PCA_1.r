# Description: Performs PCA and automatically selects enough PCs to cover 90% variance.
# Outputs are saved in the same directory as the input file.

library(readr)
library(dplyr)

# --- 1. Load the Data ---
input_file <- "C:/Users/User/Documents/Bioinformatics_Year3_Sem2/Internship/Fly Project 2_2/code/efd_normalized_final.csv"

# Extract the directory path from the input file path
output_dir <- dirname(input_file)

if (!file.exists(input_file)) {
  stop("Error: The input file '", input_file, "' was not found.")
}

full_data <- read_csv(input_file, show_col_types = FALSE)

# --- 2. Prepare Data ---
# Identify all harmonic columns
all_harmonic_columns <- grep("^[abcd][0-9]+$", names(full_data), value = TRUE)

# EXCLUDE constants (a1, b1, c1) for Correlation PCA
cols_to_remove <- c("a1", "b1", "c1")
pca_columns <- setdiff(all_harmonic_columns, cols_to_remove)

cat("Columns used for PCA:", length(pca_columns), "\n")
X <- full_data[pca_columns]

# Metadata
# --- CORRECTION: Added 'image_id' to the selection list ---
metadata <- full_data %>% dplyr::select(image_id, species, sex, cell_type, locality)

# --- 3. Perform PCA (Correlation Matrix) ---
pca_result <- prcomp(X, center = TRUE, scale. = TRUE)

# --- 4. Determine Number of PCs for 90% Variance ---
# Get the summary importance matrix
importance_matrix <- summary(pca_result)$importance
cumulative_variance <- importance_matrix[3, ]

# Find the first index where cumulative variance is >= 0.90
num_pcs_needed <- which(cumulative_variance >= 0.90)[1]

cat("----------------------------------------------------------\n")
cat(paste("Target Variance: 90%\n"))
cat(paste("PCs required:    ", num_pcs_needed, "\n"))
cat(paste("Actual Variance:", round(cumulative_variance[num_pcs_needed] * 100, 2), "%\n"))
cat("----------------------------------------------------------\n")

# --- 5. Extract the Required PCs ---
pcs <- as.data.frame(pca_result$x[, 1:num_pcs_needed])
colnames(pcs) <- paste0("PC", 1:num_pcs_needed)

# --- 6. Save Results ---
final_df <- bind_cols(metadata, pcs)

# Create full path for results
results_path <- file.path(output_dir, "pca_results_90percent.csv")
write_csv(final_df, results_path)

# --- 7. Save Variance Info ---
variance_df <- data.frame(
  PC = colnames(pcs),
  Explained_Variance = importance_matrix[2, 1:num_pcs_needed],
  Cumulative_Variance = importance_matrix[3, 1:num_pcs_needed]
)

# Create full path for variance file
variance_path <- file.path(output_dir, "pca_variance_90percent.csv")
write_csv(variance_df, variance_path)

print(paste("✅ PCA complete."))
print(paste("Results saved to:", results_path))
print(paste("Variance info saved to:", variance_path))