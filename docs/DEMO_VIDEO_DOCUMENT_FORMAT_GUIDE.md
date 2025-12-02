# Demo Video Document Format Guide

## Supported File Formats

The system supports the following file formats for demo video documents:

### Recommended Formats (Best for Video Links):
1. **`.docx`** (Microsoft Word) - **RECOMMENDED** ✅
   - Best text extraction
   - Preserves formatting
   - Easy to edit

2. **`.doc`** (Microsoft Word Legacy)
   - Works but less preferred than .docx

3. **`.pdf`** (PDF Document)
   - Good for final documents
   - Text extraction works well

4. **`.txt`** (Plain Text)
   - Simple but works
   - No formatting support

### Other Supported Formats:
- `.pptx`, `.ppt` (PowerPoint)
- `.xlsx`, `.xls` (Excel)
- `.md` (Markdown)
- `.json`, `.jsonl` (JSON)

---

## Document Structure Best Practices

### 1. Filename Convention

**Format:** `[Category]_[Product/Feature]_[Description]_demo-video.[ext]`

**Examples:**
- ✅ `DC_Edge_SnortML_Zero_Day_Machine_Learning_demo-video.docx`
- ✅ `Cloud_Edge_Dynamic_Tag-based_Policy_demo-video.docx`
- ✅ `Campus_Segmentation_Rapid_Threat_Containment_RTC_demo-video.docx`
- ✅ `Hybrid_Mesh_Firewall_Overview_demo-video.docx`

**Why this matters:**
- The filename is used for video title extraction
- RAG uses filename for semantic search
- Include key product/feature names in filename

---

### 2. Document Content Structure

#### Example 1: Single Video Document (Recommended)

```markdown
# DC Edge | Zero Day Threat Defence with Machine Learning | SnortML

## Overview

SnortML is an advanced security solution that integrates machine learning (ML) capabilities into the Snort intrusion detection and prevention system. It is designed to provide robust zero-day threat defense, particularly at the data center edge (DC Edge).

## Key Features

1. **Zero Day Threat Defense**
   - SnortML leverages machine learning to detect and defend against zero-day threats
   - ML models analyze network traffic patterns and behaviors to identify anomalies

2. **Integration with DC Edge**
   - SnortML is deployed at the data center edge
   - Provides critical layer of security at the network perimeter

3. **Machine Learning-Driven Detection**
   - Enhances detection by applying ML algorithms
   - Continuously learns from new data

## Demo Video

Watch the demonstration video to see SnortML in action:

**Demo Video:** https://www.youtube.com/watch?v=t2pwY_UiiwQ

This video demonstrates:
- Zero-day threat detection capabilities
- DC Edge integration
- Real-time threat analysis
- Automated response mechanisms

## Summary

SnortML represents a significant advancement in network security by combining the proven capabilities of Snort with the adaptive power of machine learning, delivering proactive and automated defense against both known and unknown threats at critical network junctures like the data center edge.

**Source:** DC Edge | Zero Day Threat Defence with Machine Learning | SnortML | https://youtu.be/t2pwY_UiiwQ
```

#### Example 2: Multiple Videos Document

```markdown
# Rapid Threat Containment (RTC) Demo Videos

## Overview

Rapid Threat Containment (RTC) enables organizations to quickly detect and automatically contain security threats across different network environments.

## Demo Videos

### 1. Data Centre RTC

**Title:** Data Centre Segmentation – Seamless and Automated Threat Detection and Containment (RTC)

**Description:** This demo showcases how RTC is implemented in a data centre environment using Cisco Firewall (FTD / FMC) and ACI. Key features include seamless and automated threat detection and containment.

**Video Link:** https://youtu.be/ylYY4-x_YEk

### 2. Campus RTC

**Title:** Campus Segmentation – Rapid Threat Containment (RTC) with Cisco Firewall (FTD) and Cisco ISE

**Description:** This demo focuses on RTC in a campus environment, integrating Cisco Firewall (FTD) and Cisco Identity Services Engine (ISE). It demonstrates how threats are rapidly contained using coordinated security policies and automation.

**Video Link:** https://youtu.be/iV66QbFG1x0

## Key Features

- Automated threat detection
- Rapid containment across environments
- Integration with Cisco security solutions
- Policy-based automation
```

---

## YouTube Link Format Requirements

The system recognizes the following YouTube URL formats:

### Supported Formats:

1. **Full URL with protocol:**
   ```
   https://www.youtube.com/watch?v=t2pwY_UiiwQ
   ```

2. **Short URL:**
   ```
   https://youtu.be/t2pwY_UiiwQ
   ```

3. **Embed URL:**
   ```
   https://www.youtube.com/embed/t2pwY_UiiwQ
   ```

4. **URL without protocol (will be detected):**
   ```
   youtube.com/watch?v=t2pwY_UiiwQ
   youtu.be/t2pwY_UiiwQ
   ```

### Best Practice:
- Always include the **full URL** with `https://`
- Place the video link **near relevant content** describing the video
- Include a **title or description** before/after the link for better context

---

## Content Best Practices

### ✅ DO:

1. **Include Product/Feature Names in Text:**
   ```
   SnortML provides zero-day threat defense...
   Cloud Edge enables dynamic policy enforcement...
   ```

2. **Use Descriptive Titles:**
   ```
   DC Edge | Zero Day Threat Defence with Machine Learning | SnortML
   ```

3. **Place Video Links with Context:**
   ```
   Watch the SnortML demonstration:
   https://www.youtube.com/watch?v=t2pwY_UiiwQ
   ```

4. **Include Multiple Keywords:**
   - Product name: "SnortML"
   - Category: "DC Edge"
   - Feature: "Zero Day Threat Defence"
   - Technology: "Machine Learning"

5. **Use Consistent Naming:**
   - "Cloud Edge" (not "CloudEdge" or "cloud edge" inconsistently)
   - "DC Edge" (not "Data Center Edge" and "DC Edge" mixed)

### ❌ DON'T:

1. **Don't use generic filenames:**
   - ❌ `video1.docx`
   - ❌ `demo.docx`
   - ❌ `test.docx`

2. **Don't place video links without context:**
   - ❌ Just a bare URL with no description

3. **Don't use inconsistent terminology:**
   - ❌ Mixing "Cloud Edge" and "CloudEdge"
   - ❌ Mixing "DC Edge" and "Data Center Edge"

4. **Don't use very short documents:**
   - ❌ Just a title and link (add some description)

---

## Complete Example Document (.docx format)

### Filename:
```
DC_Edge_SnortML_Zero_Day_Machine_Learning_demo-video.docx
```

### Document Content:

```
DC Edge | Zero Day Threat Defence with Machine Learning | SnortML

INTRODUCTION

SnortML is an advanced security solution that integrates machine learning (ML) capabilities into the Snort intrusion detection and prevention system. It is designed to provide robust zero-day threat defense, enhancing traditional signature-based detection with intelligent, adaptive analysis.

KEY FEATURES AND CAPABILITIES

1. Zero Day Threat Defence
   SnortML leverages machine learning to detect and defend against zero-day threats—attacks that exploit previously unknown vulnerabilities for which no signature exists. The ML models analyze network traffic patterns and behaviors to identify anomalies and potential threats in real time, even if they have not been previously cataloged.

2. Integration with DC Edge
   SnortML is deployed at the data center edge (DC Edge), providing a critical layer of security at the network perimeter. This placement allows for early detection and mitigation of threats before they can penetrate deeper into the network infrastructure.

3. Machine Learning-Driven Detection
   By incorporating ML, SnortML can adapt to evolving attack techniques and recognize malicious activity that may bypass traditional rule-based systems. The system continuously learns from new data, improving its detection accuracy over time.

4. Automated Threat Response
   Upon detecting suspicious activity, SnortML can trigger automated responses to contain and mitigate threats, reducing the window of exposure and minimizing potential damage.

5. Enhanced Security Posture
   The combination of machine learning and traditional Snort capabilities provides a multi-layered defense strategy, increasing the overall security posture of the organization. SnortML is particularly effective in environments where rapid threat detection and response are critical, such as data centers and cloud edge deployments.

DEMO VIDEO

Watch the demonstration video to see SnortML in action:

Demo Video: https://www.youtube.com/watch?v=t2pwY_UiiwQ

This video demonstrates:
- Zero-day threat detection using machine learning
- DC Edge integration and deployment
- Real-time traffic analysis and anomaly detection
- Automated threat response capabilities
- Integration with existing security infrastructure

SUMMARY

SnortML represents a significant advancement in network security by combining the proven effectiveness of Snort with the adaptive intelligence of machine learning, delivering proactive and automated defense against both known and unknown threats.

Source: DC Edge | Zero Day Threat Defence with Machine Learning | SnortML | https://youtu.be/t2pwY_UiiwQ
```

---

## Template for New Demo Video Documents

Copy this template and fill in your details:

```markdown
[Category] | [Feature/Product] | [Description]

OVERVIEW

[2-3 paragraphs describing the product/feature]

KEY FEATURES

1. [Feature 1]
   [Description]

2. [Feature 2]
   [Description]

3. [Feature 3]
   [Description]

DEMO VIDEO

Watch the demonstration video:

Demo Video: https://www.youtube.com/watch?v=[VIDEO_ID]

This video demonstrates:
- [Point 1]
- [Point 2]
- [Point 3]

SUMMARY

[1-2 paragraphs summarizing the solution]

Source: [Category] | [Feature/Product] | [Description] | https://youtu.be/[VIDEO_ID]
```

---

## File Size Recommendations

- **Maximum file size:** 100 MB
- **Recommended size:** < 10 MB for faster processing
- **Text content:** 500-5000 words is ideal (not too short, not too long)

---

## Upload Process

1. Create your document following the format above
2. Use descriptive filename with key terms
3. Include YouTube link(s) with context
4. Upload via the Document Upload interface
5. Wait for processing (usually 1-2 minutes)
6. Test by searching for your product/feature name

---

## Troubleshooting

### Video not found?
- ✅ Check YouTube URL format (must be one of the supported formats)
- ✅ Ensure URL is in the document text (not just in filename)
- ✅ Verify the video ID is correct

### Document not appearing in search?
- ✅ Check filename includes key product/feature names
- ✅ Ensure product names appear in document content
- ✅ Use consistent terminology throughout

### Wrong video returned?
- ✅ Make filename more specific (include product name)
- ✅ Add more context around the video link
- ✅ Use unique product/feature names in content

---

## Quick Checklist

Before uploading, ensure:

- [ ] Filename includes product/feature name
- [ ] Filename follows naming convention: `[Category]_[Product]_[Description]_demo-video.[ext]`
- [ ] YouTube URL is in full format: `https://www.youtube.com/watch?v=VIDEO_ID`
- [ ] Video link has descriptive context around it
- [ ] Product/feature names appear multiple times in document
- [ ] Document is in supported format (.docx recommended)
- [ ] File size is under 100 MB

---

## Example Filenames (Good vs Bad)

### ✅ Good Examples:
- `DC_Edge_SnortML_Zero_Day_Machine_Learning_demo-video.docx`
- `Cloud_Edge_Dynamic_Tag-based_Policy_demo-video.docx`
- `Campus_Segmentation_RTC_Cisco_Firewall_ISE_demo-video.docx`
- `Hybrid_Mesh_Firewall_Overview_demo-video.docx`

### ❌ Bad Examples:
- `video1.docx` (too generic)
- `demo.docx` (no product name)
- `SnortML.docx` (missing category/context)
- `test_demo_video.docx` (not descriptive)

---

**Last Updated:** 2024
**System Version:** Current

