# --- Load required packages ---
library(tidyverse)
library(MASS)

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# Ensure this input file path is correct
input_file <- "C:/Users/User/Documents/Bioinformatics_Year3_Sem2/Internship/Fly Project 2_2/code/efd_normalized_final.csv"
output_file <- "hotelling_test_results_locality.csv"
var_threshold <- 0.90  # 90% Variance

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

# 1. Load Data
if (!file.exists(input_file)) stop("Input file not found!")
df <- read_csv(input_file, show_col_types = FALSE)

# 2. Clean Data for PCA
harmonics_all <- grep("^[abcd][0-9]+$", names(df), value = TRUE)
harmonics_to_use <- setdiff(harmonics_all, c("a1", "b1", "c1"))

cat("Running PCA on", length(harmonics_to_use), "variables (excluding a1, b1, c1)...\n")

# 3. Run PCA (Correlation Matrix)
pca_mat <- df[, harmonics_to_use]
pca_result <- prcomp(pca_mat, center = TRUE, scale. = TRUE)

# 4. Determine PCs for 90% Variance
cumulative_var <- summary(pca_result)$importance[3, ]
n_pc <- which(cumulative_var >= var_threshold)[1]

cat("----------------------------------------------------------\n")
cat("PCs selected:", n_pc, "\n")
cat("Explained Variance:", round(cumulative_var[n_pc] * 100, 2), "%\n")
cat("----------------------------------------------------------\n")

# 5. Attach PC Scores
pc_scores <- as.data.frame(pca_result$x[, 1:n_pc])
colnames(pc_scores) <- paste0("PC", 1:n_pc)

df_pca <- bind_cols(
  # Ensure locality is selected here
  df %>% dplyr::select(species, sex, cell_type, locality),
  pc_scores
)

# ==============================================================================
# HOTELLING'S T2 FUNCTION
# ==============================================================================

run_hotelling <- function(sub_df, pc_cols) {
  males   <- sub_df %>% dplyr::filter(tolower(sex) == "male") %>% dplyr::select(all_of(pc_cols))
  females <- sub_df %>% dplyr::filter(tolower(sex) == "female") %>% dplyr::select(all_of(pc_cols))
  
  n_x <- nrow(males)
  n_y <- nrow(females)
  p   <- length(pc_cols)
  
  # Ensure return list has ALL fields as NA if data is insufficient
  if (n_x < p + 1 || n_y < p + 1) {
    return(list(
      Mahalanobis_D = NA, 
      T2 = NA, 
      F_stat = NA, 
      p_val = NA, 
      df1 = NA, 
      df2 = NA, 
      Note = "Sample size too small"
    ))
  }
  
  # Normal Calculation
  mean_m <- colMeans(males)
  mean_f <- colMeans(females)
  cov_m <- cov(males)
  cov_f <- cov(females)
  pooled_cov <- ((n_x - 1) * cov_m + (n_y - 1) * cov_f) / (n_x + n_y - 2)
  
  inv_cov <- tryCatch(solve(pooled_cov), error = function(e) MASS::ginv(pooled_cov))
  
  diff <- mean_m - mean_f
  D_sq <- as.numeric(t(diff) %*% inv_cov %*% diff)
  D    <- sqrt(D_sq)
  
  factor <- (n_x * n_y) / (n_x + n_y)
  T2 <- factor * D_sq
  F_stat <- ((n_x + n_y - p - 1) / ((n_x + n_y - 2) * p)) * T2
  
  df1 <- p
  df2 <- n_x + n_y - p - 1
  p_val <- 1 - pf(F_stat, df1, df2)
  
  return(list(
    Mahalanobis_D = D,
    T2 = T2, 
    F_stat = F_stat, 
    p_val = p_val, 
    df1 = df1, 
    df2 = df2,
    Note = "Success"
  ))
}

# ==============================================================================
# RUN TESTS PER GROUP (MODIFIED FOR LOCALITY)
# ==============================================================================

# --- CHANGE 1: Added locality to distinct() and arrange() ---
groups <- df_pca %>% 
  dplyr::distinct(species, locality, cell_type) %>% 
  dplyr::arrange(species, locality, cell_type)

results_list <- list()
counter <- 1

cat("Running Hotelling's T2 tests (grouping by Species + Locality)...\n")

for (i in 1:nrow(groups)) {
  sp  <- groups$species[i]
  loc <- groups$locality[i]  # --- CHANGE 2: Extract Locality ---
  ct  <- groups$cell_type[i]
  
  # --- CHANGE 3: Added locality to filter() ---
  subset_data <- df_pca %>% 
    dplyr::filter(species == sp, locality == loc, cell_type == ct)
  
  n_m <- sum(tolower(subset_data$sex) == "male")
  n_f <- sum(tolower(subset_data$sex) == "female")
  
  cat(sprintf("  Processing: %s (%s) | %s (M:%d, F:%d)... ", sp, loc, ct, n_m, n_f))
  
  if (n_m == 0 || n_f == 0) {
    cat("Skipping (Missing Data)\n")
    next
  }
  
  res <- run_hotelling(subset_data, colnames(pc_scores))
  
  # Store Result
  results_list[[counter]] <- data.frame(
    Species = sp,
    Locality = loc,  # --- CHANGE 4: Add Locality column to output ---
    Cell_Type = ct,
    Male_N = n_m,
    Female_N = n_f,
    PCs_Used = n_pc,
    Mahalanobis_Dist = round(as.numeric(res$Mahalanobis_D), 4),
    T2_Statistic = round(as.numeric(res$T2), 2),
    F_Statistic = round(as.numeric(res$F_stat), 2),
    P_Value = format.pval(as.numeric(res$p_val), digits = 4),
    Significance = ifelse(!is.na(res$p_val) & as.numeric(res$p_val) < 0.05, "*", "ns"),
    Note = res$Note
  )
  
  cat(res$Note, "\n")
  counter <- counter + 1
}

# ==============================================================================
# SAVE
# ==============================================================================
if (length(results_list) > 0) {
  final_results <- do.call(rbind, results_list)
  
  # Save in the same directory as input if possible, or use the configured path
  # To force it to save in the same folder as the input file:
  output_path <- file.path(dirname(input_file), output_file)
  
  write_csv(final_results, output_path)
  
  cat("\n======================================================\n")
  cat("DONE! Results saved to:", output_path, "\n")
  print(head(final_results))
} else {
  cat("\nNo valid comparisons found.\n")
}