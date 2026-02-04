# Sexual-Dimorphism-in-Flies-Wing-Cells

Geometric Morphometrics Pipeline for Fly Wing AnalysisThis repository contains a complete bioinformatics pipeline for analyzing wing shape variations in Diptera species (e.g., Calliphora vicina, Chrysomya albiceps) using Elliptic Fourier Descriptors (EFD).The project investigates Sexual Dimorphism and Geographic Variation (Locality) by processing wing images, generating shape coefficients, performing statistical tests (PCA, MANOVA, Hotelling's $T^2$), and creating interactive 3D visualizations.

Repository Structure

Data Processing
efd_generation.r: The starting point. Reads raw wing images, normalizes them (size, rotation, phase) using Momocs, and generates Elliptic Fourier Descriptors. Uses parallel processing to handle large datasets.

PCA_1.r: Performs Principal Component Analysis (PCA) on the normalized EFD coefficients. It automatically selects the number of Principal Components (PCs) required to explain 90% of the variance.
