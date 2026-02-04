# Sexual Dimorphism in Fly Wing Cells

## 🧬 Geometric Morphometrics Pipeline
This repository contains a complete bioinformatics pipeline for analyzing wing shape variations in Diptera species (e.g., *Calliphora vicina*, *Chrysomya albiceps*) using **Elliptic Fourier Descriptors (EFD)**.

The project investigates **Sexual Dimorphism** and **Geographic Variation** by processing wing images, generating shape coefficients, performing statistical tests, and creating interactive 3D visualizations.

---

## 📂 Repository Structure

### 1. Data Processing (R)
* **`efd_generation.r`**:  
    The pipeline entry point. It reads raw wing images from a structured directory, normalizes them (size, rotation, phase) using the `Momocs` package, and generates Elliptic Fourier Descriptors. It utilizes parallel processing for efficiency.
* **`PCA_1.r`**:  
    Performs Principal Component Analysis (PCA) on the normalized EFD coefficients. It automatically calculates and selects the specific number of Principal Components (PCs) required to explain **90% of the cumulative variance**.

### 2. Statistical Analysis (R)
* **`manova.r`**:  
    Runs Multivariate Analysis of Variance (MANOVA) to calculate the percentage of shape variation attributed to Species, Sex, Locality, and their interactions.
* **`hottelling.r`**:  
    Performs **Hotelling’s $T^2$ test** to determine if the shape difference between Males and Females is statistically significant within specific populations (Species + Locality).

### 3. Visualization (Python)
* **`contour_check.py`**:  
    Reconstructs the average wing shapes from EFD coefficients. Plots Mean Male vs. Mean Female outlines to visually verify shape differences.
* **`plot_PCA_1.py`**:  
    Generates high-quality, interactive **3D Scatter Plots** using Plotly. Features custom styling (Lato font), grouping by population, and detailed hover metadata.

---

## 🛠️ Dependencies

To run these scripts, you will need the following libraries installed.

### R Packages
```r
install.packages(c("Momocs", "imager", "tidyverse", "foreach", "doParallel", "MASS", "ggplot2", "scales"))
