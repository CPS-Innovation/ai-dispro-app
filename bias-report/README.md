***

# 📝 Bias Report Orchestrator

This module runs a disproportionality (DISPRO) analysis across all counterfactual pairs defined in the project’s dataset. It uses Azure AI Foundry to evaluate whether the analysis tool behaves consistently across different counterfactual scenarios and produces a consolidated report.

***

## 📁 Project Requirements

Before running the notebook, make sure the following prerequisites are met.


## 1. Environment Variables

Create a `.env` file in the project root containing the Azure AI Foundry credentials required by the code.  
The notebook expects these variables to be present:

```env
AZURE_AI_FOUNDRY_API_KEY=<your-api-key>
AZURE_AI_FOUNDRY_ENDPOINT=<your-endpoint-url>
AZURE_AI_FOUNDRY_API_VERSION=<your-api-version>
AZURE_AI_FOUNDRY_DEPLOYMENT_NAME=<your-deployment-name>
```



## 2. Required Data Files

Place the following CSV files into the project's `data/` directory:

*   `prompts.csv`
*   `senarios.csv`

Both files can be downloaded from the project’s Azure Blob Storage container.

These files provide:

*   Prompt templates
*   Counterfactual scenario definitions


## 3. Running the Disproportionality Analysis

Once the `.env` file is configured and the dataset is in place:

1.  Open **`bias_analysis.ipynb`**
2.  Run **all cells** from top to bottom

The notebook will:

*   Load prompts and scenario pairs
*   Send each pair to the DISPRO analysis tool
*   Compare outputs across the pairs
*   Produce a summary report evaluating whether the DISPRO tool behaves equitably


## 📊 Output

The notebook generates:

*   A set of results for each counterfactual scenario
*   A consolidated report summarizing whether DISPRO performs consistently across demographic groups



