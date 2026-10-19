

# AWS Regions
<a name="aws-regions"></a>

When you are preparing to deploy a workload, consider which Region or Regions best meet your needs. For example, select a Region that has the AWS services and features that you need. Also, you can lower network latency when you select a Region that is close to the majority of your users.

Your account determines the Regions that are available to you.

**Account types**
+ An AWS account provides multiple Regions so that you can create AWS resources in the locations that meet your requirements. For example, you want to create resources in Europe to be closer to your European customers or to meet legal requirements.
+ An AWS GovCloud (US) account provides access to the AWS GovCloud (US-West) Region and the AWS GovCloud (US-East) Region. For more information, see [AWS GovCloud (US)](https://aws.amazon.com/govcloud-us/).
+ An Amazon AWS (China) account provides access to the Beijing and Ningxia Regions only. For more information, see [Amazon Web Services in China](https://www.amazonaws.cn/about-aws/china/).

You can't describe or access the Regions of one type of account from another. For example, you can't access the AWS GovCloud (US) Regions or the China Regions from an AWS account.

For more information about the availability of AWS services by Region for AWS accounts and AWS GovCloud (US) accounts, see [AWS Services by Region](https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/).

## Available AWS Regions
<a name="available-regions"></a>

The geography for a Region is the specific physical location of its infrastructure. This information can help you meet your regulatory, compliance, and operational requirements.

There are currently 34 Regions. The following table lists the Regions provided by an AWS account.


| Code | Name | AZs | Geography | Opt-in status | 
| --- | --- | --- | --- | --- | 
| us-east-1 | US East (N. Virginia) | 6 | United States of America | Not required | 
| us-east-2 | US East (Ohio) | 3 | United States of America | Not required | 
| us-west-1 | US West (N. California) | 3  † | United States of America | Not required | 
| us-west-2 | US West (Oregon) | 4 | United States of America | Not required | 
| af-south-1 | Africa (Cape Town) | 3 | South Africa | Required | 
| ap-east-1 | Asia Pacific (Hong Kong) | 3 | Hong Kong | Required | 
| ap-south-2 | Asia Pacific (Hyderabad) | 3 | India | Required | 
| ap-southeast-3 | Asia Pacific (Jakarta) | 3 | Indonesia | Required | 
| ap-southeast-5 | Asia Pacific (Malaysia) | 3 | Malaysia | Required | 
| ap-southeast-4 | Asia Pacific (Melbourne) | 3 | Australia | Required | 
| ap-south-1 | Asia Pacific (Mumbai) | 3 | India | Not required | 
| ap-southeast-6 | Asia Pacific (New Zealand) | 3 | New Zealand | Required | 
| ap-northeast-3 | Asia Pacific (Osaka) | 3 | Japan | Not required | 
| ap-northeast-2 | Asia Pacific (Seoul) | 4 | South Korea | Not required | 
| ap-southeast-1 | Asia Pacific (Singapore) | 3 | Singapore | Not required | 
| ap-southeast-2 | Asia Pacific (Sydney) | 3 | Australia | Not required | 
| ap-east-2 | Asia Pacific (Taipei) | 3 | Taiwan | Required | 
| ap-southeast-7 | Asia Pacific (Thailand) | 3 | Thailand | Required | 
| ap-northeast-1 | Asia Pacific (Tokyo) | 4 | Japan | Not required | 
| ca-central-1 | Canada (Central) | 3 | Canada | Not required | 
| ca-west-1 | Canada West (Calgary) | 3 | Canada | Required | 
| eu-central-1 | Europe (Frankfurt) | 3 | Germany | Not required | 
| eu-west-1 | Europe (Ireland) | 3 | Ireland | Not required | 
| eu-west-2 | Europe (London) | 3 | United Kingdom | Not required | 
| eu-south-1 | Europe (Milan) | 3 | Italy | Required | 
| eu-west-3 | Europe (Paris) | 3 | France | Not required | 
| eu-south-2 | Europe (Spain) | 3 | Spain | Required | 
| eu-north-1 | Europe (Stockholm) | 3 | Sweden | Not required | 
| eu-central-2 | Europe (Zurich) | 3 | Switzerland | Required | 
| il-central-1 | Israel (Tel Aviv) | 3 | Israel | Required | 
| mx-central-1 | Mexico (Central) | 3 | Mexico | Required | 
| me-south-1 | Middle East (Bahrain) | 3 | Bahrain | Required | 
| me-central-1 | Middle East (UAE) | 3 | United Arab Emirates | Required | 
| sa-east-1 | South America (São Paulo) | 3 | Brazil | Not required | 

† Newer accounts can access two Availability Zones in US West (N. California).

## Opt-in status
<a name="regions-opt-in-status"></a>

To use a Region introduced after March 20, 2019, you must enable the Region before you can access it. The earlier Regions are enabled by default, which means that you can begin creating resources immediately.

You can enable a Region in one of the following ways:

------
#### [ AWS Global View console ]

**To enable a Region**

1. Sign in to the [AWS Global View console](https://console.aws.amazon.com/awsglobalview/home#RegionsAndZones).

1. From the navigation pane, choose **Regions and Zones**.

1. From the **Regions** tab, find Region that you want to enable. You can scroll down the list or enter a term in the Search field.

1. Select the row for the Region.

1. Choose **Enable Region**.

1. On the **Enable Region** pop-up, choose **Enable Region**.

------
#### [ AWS Billing and Cost Management console ]

To enable a Region from the AWS Billing and Cost Management console, see [Enable or disable AWS Regions in your account](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-regions.html) in the *AWS Account Management Reference Guide*.

------

**Regions enabled by default**
+ US East (N. Virginia)
+ US East (Ohio)
+ US West (N. California)
+ US West (Oregon)
+ Asia Pacific (Mumbai)
+ Asia Pacific (Osaka)
+ Asia Pacific (Seoul)
+ Asia Pacific (Singapore)
+ Asia Pacific (Sydney)
+ Asia Pacific (Tokyo)
+ Canada (Central)
+ Europe (Frankfurt)
+ Europe (Ireland)
+ Europe (London)
+ Europe (Paris)
+ Europe (Stockholm)
+ South America (São Paulo)

**Regions disabled by default**
+ Africa (Cape Town)
+ Asia Pacific (Hong Kong)
+ Asia Pacific (Hyderabad)
+ Asia Pacific (Jakarta)
+ Asia Pacific (Malaysia)
+ Asia Pacific (Melbourne)
+ Asia Pacific (New Zealand)
+ Asia Pacific (Taipei)
+ Asia Pacific (Thailand)
+ Canada West (Calgary)
+ Europe (Milan)
+ Europe (Spain)
+ Europe (Zurich)
+ Israel (Tel Aviv)
+ Mexico (Central)
+ Middle East (Bahrain)
+ Middle East (UAE)

## View Region information
<a name="regions-example-commands"></a>

You can list the Regions for your account, get the opt-in status of a Region, and get the long name of a Region.

------
#### [ Console ]

**To view Regions and their status in the console**

1. Sign in to the [AWS Global View console](https://console.aws.amazon.com/awsglobalview/home#RegionsAndZones).

1. On the **Regions** tab, the **Status** column shows whether a Region is **Enabled by default**, **Enabled**, or **Disabled**.

1. To filter the Regions by a particular status, choose the Search field, choose **Status**, and then choose a value.

------
#### [ AWS CLI ]

**To list the Regions enabled by default**  
Use the following AWS CLI [list-regions](https://docs.aws.amazon.com/cli/latest/reference/account/list-regions.html) command.

```
aws account list-regions --region-opt-status-contains ENABLED_BY_DEFAULT --query Regions[*].RegionName
```

The following is example output:

```
[
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-northeast-3",
    "ap-south-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ca-central-1",
    "eu-central-1",
    "eu-north-1",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "sa-east-1",
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2"
]
```

**To list the Regions enabled for your account**  
Use the following AWS CLI [list-regions](https://docs.aws.amazon.com/cli/latest/reference/account/list-regions.html) command to list both Regions enabled by default and Regions enabled for your account.

```
aws account list-regions --region-opt-status-contains ENABLED_BY_DEFAULT ENABLED --query Regions[*].RegionName
```

**To get the opt-in status of a Region**  
Use the following AWS CLI [get-region-opt-status](https://docs.aws.amazon.com/cli/latest/reference/account/get-region-opt-status.html) command.

```
aws account get-region-opt-status --region-name af-south-1
```

The following is example output:

```
{
    "RegionName": "af-south-1",
    "RegionOptStatus": "DISABLED"
}
```

**To get the long name of a Region**  
Use the following AWS CLI [get-parameters-by-path](https://docs.aws.amazon.com/cli/latest/reference/ssm/get-parameters-by-path.html) command. Replace {{region-code}} with the code for the Region. You might need to modify the quotes to get the example to work with your terminal.

```
aws ssm get-parameters-by-path \
    --path /aws/service/global-infrastructure/regions/{{region-code}} \
    --query 'Parameters[?Name.contains(@,`longName`)].Value' \
    --output text
```

The following is example output where {{region-code}} is `af-south-1`:

```
Africa (Cape Town)
```

------
#### [ PowerShell ]

**To list the Regions enabled by default**  
Use the following AWS Tools for PowerShell [Get-ACCTRegionList](https://docs.aws.amazon.com/powershell/latest/reference/items/Get-ACCTRegionList.html) command.

```
(Get-ACCTRegionList -RegionOptStatusContain ENABLED_BY_DEFAULT).RegionName
```

The following is example output:

```
ap-northeast-1
ap-northeast-2
ap-northeast-3
ap-south-1
ap-southeast-1
ap-southeast-2
ca-central-1
eu-central-1
eu-north-1
eu-west-1
eu-west-2
eu-west-3
sa-east-1
us-east-1
us-east-2
us-west-1
us-west-2
```

**To list the Regions enabled for your account**  
Use the following AWS Tools for PowerShell [Get-ACCTRegionList](https://docs.aws.amazon.com/powershell/latest/reference/items/Get-ACCTRegionList.html) command to list both Regions enabled by default and Regions enabled for your account.

```
(Get-ACCTRegionList -RegionOptStatusContain ENABLED_BY_DEFAULT,ENABLED).RegionName
```

**To get the opt-in status of a Region**  
Use the following AWS Tools for PowerShell [Get-ACCTRegionOptStatus](https://docs.aws.amazon.com/powershell/latest/reference/items/Get-ACCTRegionOptStatus.html) command.

```
Get-ACCTRegionOptStatus -RegionName af-south-1
```

The following is example output:

```
Value
-----
DISABLED
```

**To get the long name of a Region**  
Use the following AWS Tools for PowerShell [Get-SSMParametersByPath](https://docs.aws.amazon.com/powershell/latest/reference/items/Get-SSMParametersByPath.html) command. Replace {{region-code}} with the code for the Region.

```
(Get-SSMParametersByPath -Path /aws/service/global-infrastructure/regions/{{region-code}} | Where-Object Name -like "*longName*").Value
```

The following is example output where {{region-code}} is `af-south-1`:

```
Africa (Cape Town)
```

------