# Opinion Compass

## Introduction and Features
The Opinion Compass is designed to analyze the opinions of individuals based on specified statements. Users can simply provide the name of the person whose opinions they want to analyze along with the specific opinion statement. 

Key functionalities:
- **AI Analysis:** Leverages AI technology to provide analysis on the provided opinions.
- **Evidence Consideration:** Includes various pieces of evidence that influence the final analysis, enhancing the comprehensiveness of the insights.

### Evidence Scoring

The Opinion Compass analyzes multiple pieces of evidence and provides detailed scoring:

Each piece of evidence is evaluated with two key metrics:
- **Opinion Score (-1.0 to 1.0)**: Indicates how strongly the evidence supports or opposes the opinion
  - 1.0: Strongly supports the opinion
  - 0.0: Neutral stance
  - -1.0: Strongly opposes the opinion
- **Relevance Score (0.0 to 1.0)**: Shows how relevant the evidence is to the opinion
  - 1.0: Highly relevant evidence
  - 0.0: Not relevant

### Aggregated Score
The system produces a final aggregated score (-1.0 to 1.0) that considers all pieces of evidence, weighted by their relevance. This provides a comprehensive assessment of the person's stance on the given opinion.

Example output of single evidence data point:
```json
    {
        "source": "X/Twitter",
        "score": -0.8,
        "relevance": 1,
        "text": "This declaration is a sad testament of bad Brusselian leadership. While President @realDonaldTrump and President Putin negotiate on peace, EU officials issue worthless statements.\n\nYou can’t request a seat at the negotiating table. You have to earn it! Through strength, good leadership and smart diplomacy.\n\nThe position of Brussels - to support killing as long as it takes - is morally and politically unacceptable.",
        "url": "https://x.com/PM_ViktorOrban/status/1889976335897899377"
    }
```

## Tutorial Section
### How to use Opinion Compass to analyze opinions
1. Ensure you have an Apify account.
2. Create a new Actor run with the following input JSON:

```json
{
  "person": "Tomio Okamura",
  "opinion": "Democratic values are important."
}
```

3. Run the Actor and retrieve the final analysis as output.

## Pricing Explanation
The Opinion Compass operates on a **Pay Per Event** pricing model

What is charged for
| Feature                | Description                                             | Price    |
|------------------------|---------------------------------------------------------|----------|
| Actor Start per 1 GB   | Flat fee for starting an Actor run for each 1 GB of memory | $0.005  |
| AI Analysis            | Produces final AI analysis| $0.01   |
| Piece of Evidence      | Additional fee for each piece of evidence considered. | $0.02   |


## Input and Output Examples
### Input requirements
The following JSON input format must be used when running the Actor:

```json
{
  "person": "Tomio Okamura",
  "opinion": "Democratic values are important."
}
```

### Expected Output
The output from the Actor will be structured in JSON as stored in the default KV store under `ai-analysis` as follows:

```json
{
  "analysis": {
    "person": "Tomio Okamura",
    "opinion": "Democratic values are important.",
    "score": 0.5,
    "explanation": "The score is based on the evidence that the person identifies with the opinion. It ranges from -1.0 to 1.0. The higher the score, the more the person identifies with the opinion. 1 means strong identification, -1 means strong opposition, 0 means inconclusive evidence.",
  }
}
```

## FAQ, Disclaimers, and Support
- **Can I use the Opinion Compass for any public opinion?**
  Yes, as long as the opinion is public and can be addressed ethically.

- **What should I do if I encounter errors?**
  Check your input format and ensure required fields are included. If issues persist, consult the support channels.
  You are only charged for the results if they can be produced.

- **How accurate are the results?**
  The accuracy depends on the available evidence and context. The system uses advanced AI models but results should be considered as analytical insights rather than definitive truth.

- **What sources does Opinion Compass use?**
  The system analyzes publicly available information from X(Twitter) and Instagram. More sources will be added in the future.

- **How recent is the analyzed data?**
  The system analyzes the most recent data available.

- **Can I analyze multiple opinions at once?**
  Currently, the system processes one person-opinion pair at a time. For multiple analyses, you'll need to run separate queries.

- **How long does an analysis typically take?**
  Analysis time varies based on the complexity and amount of available evidence, but typically takes a few minutes to complete.

- **Is there a limit to the number of analyses I can run?**
  No, but standard pricing applies to each analysis run. Consider your usage needs and budget accordingly.

For further assistance, please create an issue or contact the author.

## Feedback
Your feedback is important to us! If you have suggestions or find any issues, please reach out.