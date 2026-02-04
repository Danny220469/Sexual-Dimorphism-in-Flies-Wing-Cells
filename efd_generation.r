library(imager)
library(Momocs)
library(stringr)
library(foreach)
library(doParallel)

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# Ensure this path matches your actual folder location
root_folder <- "C:/Users/User/Documents/Bioinformatics_Year3_Sem2/Internship/Fly Project 2_2"
output_csv  <- "efd_normalized_final.csv"
harmonics   <- 10

# ==============================================================================
# 1. SETUP PARALLEL PROCESSING
# ==============================================================================
num_cores <- parallel::detectCores() - 1
cl <- makeCluster(num_cores)
registerDoParallel(cl)

cat(paste("Parallel processing enabled using", num_cores, "cores.\n"))

# ==============================================================================
# 2. NORMALIZATION FUNCTIONS (From normalisation_scale_rotate_phase.R)
# ==============================================================================

# ---------- Size normalization (semi-major axis scaling) ---------------------
size_normalize_coeffs <- function(an, bn, cn, dn, tol = 1e-9) {
  a1 <- an[1]; b1 <- bn[1]; c1 <- cn[1]; d1 <- dn[1]
  S1 <- a1^2 + b1^2 + c1^2 + d1^2
  D  <- (a1^2 + c1^2 - b1^2 - d1^2)
  E  <- 2 * (a1 * b1 + c1 * d1)
  disc <- sqrt(D^2 + E^2)
  lambda1 <- (S1 + disc)/2
  if (lambda1 < tol) stop("Degenerate first harmonic: semi-major axis ~ 0")
  A_len <- sqrt(lambda1)
  
  # Scale all harmonics by A_len
  list(
    an = an / A_len,
    bn = bn / A_len,
    cn = cn / A_len,
    dn = dn / A_len
  )
}

# ---------- Rotation normalization (spatial) ---------------------------------
rotation_normalize_coeffs <- function(an, bn, cn, dn) {
  # Left rotation using first harmonic only
  a1 <- an[1]; b1 <- bn[1]; c1 <- cn[1]; d1 <- dn[1]
  A11 <- a1*a1 + b1*b1
  A22 <- c1*c1 + d1*d1
  A12 <- a1*c1 + b1*d1
  phi <- 0.5 * atan2(2 * A12, A11 - A22)
  co <- cos(phi); si <- sin(phi)
  
  a_rot <- co*an + si*cn
  b_rot <- co*bn + si*dn
  c_rot <- -si*an + co*cn
  d_rot <- -si*bn + co*dn
  
  list(
    an = a_rot,
    bn = b_rot,
    cn = c_rot,
    dn = d_rot
  )
}

# ---------- Starting point normalization (parametric phase) ------------------
starting_point_normalize_coeffs <- function(an, bn, cn, dn, H = 10) {
  # Aligns parametric starting point so that the major axis of 1st harmonic is at t=0
  a1 <- an[1]; b1 <- bn[1]
  phi <- atan2(b1, a1)
  
  an_new <- numeric(H)
  bn_new <- numeric(H)
  cn_new <- numeric(H)
  dn_new <- numeric(H)
  
  for (n in 1:H) {
    th <- -n * phi
    co <- cos(th)
    si <- sin(th)
    
    an_new[n] <- co * an[n] - si * bn[n]
    bn_new[n] <- si * an[n] + co * bn[n]
    cn_new[n] <- co * cn[n] - si * dn[n]
    dn_new[n] <- si * cn[n] + co * dn[n]
  }
  
  list(
    an = an_new,
    bn = bn_new,
    cn = cn_new,
    dn = dn_new
  )
}

# ==============================================================================
# 3. IMAGE PROCESSING FUNCTION
# ==============================================================================
process_single_image <- function(file_path, species, locality, sex, cell_type, n_harmonics) {
  tryCatch({
    # 1. Load Image
    img <- load.image(file_path)
    
    # Mirroring (kept from original efd_generation.r)
    img <- mirror(img, "y") 
    
    # 2. Extract Contours
    contours <- imager::contours(img)
    if (is.null(contours) || length(contours) == 0) return(NULL)
    
    contour_lengths <- sapply(contours, function(c) length(c$x))
    largest_contour <- contours[[which.max(contour_lengths)]]
    if (length(largest_contour$x) < 50) return(NULL)
    
    # 3. Calculate Raw EFD (Un-normalized)
    mtx <- matrix(c(largest_contour$x, largest_contour$y), ncol = 2)
    # norm=FALSE is CRITICAL here so we can apply our own functions
    efd_res <- efourier(mtx, nb.h = n_harmonics, norm = FALSE)
    
    raw_an <- unlist(efd_res$an)
    raw_bn <- unlist(efd_res$bn)
    raw_cn <- unlist(efd_res$cn)
    raw_dn <- unlist(efd_res$dn)
    
    # 4. Apply 3-Step Normalization Pipeline
    # Step A: Size
    size_out <- size_normalize_coeffs(raw_an, raw_bn, raw_cn, raw_dn)
    
    # Step B: Rotation
    rot_out <- rotation_normalize_coeffs(size_out$an, size_out$bn, size_out$cn, size_out$dn)
    
    # Step C: Phase (Starting Point)
    final_out <- starting_point_normalize_coeffs(rot_out$an, rot_out$bn, rot_out$cn, rot_out$dn, H = n_harmonics)
    
    # 5. Format Output
    meta_df <- data.frame(image_id=basename(file_path), species=species, 
                          sex=sex, locality=locality, cell_type=cell_type)
    
    coeff_list <- c(final_out$an, final_out$bn, final_out$cn, final_out$dn)
    names(coeff_list) <- c(paste0("a", 1:n_harmonics), paste0("b", 1:n_harmonics),
                           paste0("c", 1:n_harmonics), paste0("d", 1:n_harmonics))
    
    return(cbind(meta_df, as.data.frame(t(coeff_list))))
    
  }, error = function(e) {
    # It's good practice to print the error if single-threading, but in parallel we return NULL to avoid crashing
    return(NULL) 
  })
}

# ==============================================================================
# 4. MAIN EXECUTION
# ==============================================================================

if (!dir.exists(root_folder)) stop("Root folder not found! Please check the path in CONFIGURATION.")

# --- A. Scan folders and build a Job List ---
cat("Scanning folders to build job list...\n")
job_list <- data.frame()

l1_dirs <- list.dirs(root_folder, full.names = TRUE, recursive = FALSE)
for (l1_path in l1_dirs) {
  parts_l1 <- str_split(basename(l1_path), "_")[[1]]
  if (length(parts_l1) >= 2) {
    locality <- tail(parts_l1, 1); species <- paste(head(parts_l1, -1), collapse = "_")
  } else { species <- basename(l1_path); locality <- "Unknown" }
  
  l2_dirs <- list.dirs(l1_path, full.names = TRUE, recursive = FALSE)
  for (l2_path in l2_dirs) {
    parts_l2 <- str_split(basename(l2_path), "_", n = 2)[[1]]
    if (length(parts_l2) == 2) { sex <- parts_l2[1]; cell_type <- parts_l2[2] }
    else { sex <- basename(l2_path); cell_type <- "Unknown" }
    
    images <- list.files(l2_path, pattern = "\\.(png|jpg|jpeg|tif|bmp)$", full.names = TRUE, recursive = TRUE)
    
    if (length(images) > 0) {
      temp_df <- data.frame(
        file_path = images,
        species = species,
        locality = locality,
        sex = sex,
        cell_type = cell_type,
        stringsAsFactors = FALSE
      )
      job_list <- rbind(job_list, temp_df)
    }
  }
}

cat(paste("Found", nrow(job_list), "images. Starting parallel processing...\n"))

# --- B. Run Parallel Loop ---
results_df <- foreach(i = 1:nrow(job_list), .combine = rbind, .packages = c("imager", "Momocs")) %dopar% {
  
  row <- job_list[i, ]
  
  process_single_image(
    file_path = row$file_path,
    species = row$species,
    locality = row$locality,
    sex = row$sex,
    cell_type = row$cell_type,
    n_harmonics = harmonics
  )
}

stopCluster(cl)

# ==============================================================================
# 5. SAVE RESULTS
# ==============================================================================
if (!is.null(results_df) && nrow(results_df) > 0) {
  write.csv(results_df, output_csv, row.names = FALSE)
  
  cat("\n======================================================\n")
  cat("DONE! Saved to:", output_csv, "\n")
  cat("Total Processed:", nrow(results_df), "\n")
} else {
  cat("No images were successfully processed.\n")
}