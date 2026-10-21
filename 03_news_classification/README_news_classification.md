# Economic News Classification (Python)

This module classifies Colombian news articles as economic or non-economic using **TF-IDF text features** and two supervised models: **L1-regularized logistic regression** and a **linear-kernel support vector machine (SVM)**.

## Inputs and output

- **Private labeled training dataset** (`data_train_texto_completo.xlsx`): must contain `texto` (article text) and `econ` (economic relevance label).
- **Spanish stopword list** (`stopwords_es.xlsx`): must contain a column named `palabra`. The project's stopword resource is attributed to the **Bank of Spain (Banco de España)** and is **available upon request**, subject to any applicable permissions.
- **Consolidated news dataset** (`base_texto.xlsx`): produced by the preceding R consolidation step; must contain `texto`.
- **Output** (`clasificacion_texto.xlsx`): the incoming dataset with two additional predictions, `econ_logit` and `econ_svm`.

## Data availability

**The labeled training data cannot be made public.** It is not included in this repository. The stopword list is likewise not distributed here; inquiries about access can be made to the project author. Consequently, reproducing the fitted models requires access to these inputs. The source code is shared to document the methodology.

## Usage

Install dependencies:

```bash
pip install pandas openpyxl scikit-learn
```

Run from a terminal or configure equivalent script arguments in Spyder:

```bash
python Logit_Texto.py --training path/to/data_train_texto_completo.xlsx --stopwords path/to/stopwords_es.xlsx --input path/to/base_texto.xlsx --output clasificacion_texto.xlsx
```

The script evaluates both models on a held-out sample, then refits them using the full labeled dataset to generate predictions for new articles. Text normalization is applied consistently across training and prediction data.

## Broader project

The results support a **subsequent AI-based relevance classification stage**. That stage and its evolving prompt are not included in this module. The wider project also includes daily Google News RSS collection and consolidation in R.

## AI assistance

Generative AI assisted with code development and refinement. This is separate from its use as a later-stage news classifier.
