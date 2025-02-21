# README for Opinion Compass

## Introduction and Features
The Opinion Compass is designed to analyze the opinions of individuals based on specified statements. Users can simply provide the name of the person whose opinions they want to analyze along with the specific opinion statement. 

Key functionalities:
- **AI Analysis:** Leverages AI technology to provide in-depth analysis on the opinions provided.
- **Evidence Consideration:** Includes various pieces of evidence that influence the final analysis, enhancing the comprehensiveness of the insights.

| Feature                | Description                                             |
|------------------------|---------------------------------------------------------|
| Actor Start per 1 GB  | Flat fee for starting an Actor run for each 1 GB of memory at $0.005. |
| AI Analysis            | Produces final AI analysis with a fee of $0.01.       |
| Piece of Evidence      | Additional fee of $0.02 for each piece of evidence considered. |

Apify's platform enhances the Opinion Compass by providing API access, scheduling capabilities, and proxy rotation.

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
The Opinion Compass operates on a **Pay Per Event** pricing model:
- Each event generation will incur varying costs based on usage.

Expectations for costs in common usage scenarios:
- Starting the Actor with 1 GB of memory: $0.005
- Generating an AI analysis: $0.01
- Considering additional evidence: $0.02 per piece.

### How much does it cost to analyze an opinion?
Analyzing a single opinion with basic functionality will cost approximately **$0.03** for the AI analysis and evidence consideration, excluding the Actor run cost.

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
The output from the Actor will be structured in JSON as follows:

```json
{
  "analysis": {
    "person": "Tomio Okamura",
    "opinion": "Democratic values are important.",
    "results": {
      "summary": "The analysis shows a strong belief in democratic values.",
      "evidence": [
        "Evidence 1",
        "Evidence 2"
      ]
    }
  }
}
```

## FAQ, Disclaimers, and Support
- **Can I use the Opinion Compass for any public opinion?**
  Yes, as long as the opinion is public and can be addressed ethically.
  
- **What should I do if I encounter errors?**
  Check your input format and ensure required fields are included. If issues persist, consult the support channels.

For further assistance, please visit our support section or contact us directly.

## Feedback
Your feedback is important to us! If you have suggestions or find any issues, please reach out through our feedback form. 

---

With these guidelines, you can effectively utilize the Opinion Compass to analyze and generate insights on various personal opinions using Apify's robust features.