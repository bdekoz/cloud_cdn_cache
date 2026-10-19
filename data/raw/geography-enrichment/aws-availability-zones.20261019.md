

# AWS Availability Zones
<a name="aws-availability-zones"></a>

Each Region has at least three Availability Zones. This helps you to design highly available applications on AWS.

The code for an Availability Zone is its Region code followed by a letter identifier. For example, `us-east-2a`, `us-east-2b`, and `us-east-2c` are the Availability Zones in the `us-east-2` Region.

For accounts created before November 2025, in our oldest Regions, we independently map Availability Zones to codes for each AWS account. For example, the `us-east-1a` Availability Zone for your account might not be the same physical location as it is in another account. Accounts created starting November 2025, get the same Availability Zones mapped to codes. For more information, see [Regions with independently mapped Availability Zones](az-ids.md#independently-mapped-azs).

Each Availability Zone has an AZ ID, which is the same physical location in every AWS account. An AZ ID consists of a Region-specific prefix, followed by `-az`, followed by a number. For example, `euw1-az1`, `euw1-az2`, and `euw1-az3` are the AZ IDs for the Availability Zones in the `eu-west-1` Region. For more information, see [AZ IDs](az-ids.md).

The geography for an Availability Zone is the specific physical location of its infrastructure. This information can help you meet your regulatory, compliance, and operational requirements.

**Topics**
+ [North America](#zones-north-america)
+ [Africa](#zones-africa)
+ [Asia Pacific](#zones-asia-pacific)
+ [Europe](#zones-europe)
+ [Middle East](#zones-middle-east)
+ [South America](#zones-south-america)
+ [Constrained Availability Zones](#constrained-zones)
+ [View Availability Zone information](#zones-example-commands)

## North America
<a name="zones-north-america"></a>

The following table lists the Availability Zones in North America.


| AZ ID | Region | Geography | 
| --- | --- | --- | 
| use1-az1 | us-east-1 | Virginia, United States of America | 
| use1-az2 | us-east-1 | Virginia, United States of America | 
| use1-az3 | us-east-1 | Virginia, United States of America | 
| use1-az4 | us-east-1 | Virginia, United States of America | 
| use1-az5 | us-east-1 | Virginia, United States of America | 
| use1-az6 | us-east-1 | Virginia, United States of America | 
| Coming in 2026 | us-east-1 | Maryland, United States of America | 
| use2-az1 | us-east-2 | Ohio, United States of America | 
| use2-az2 | us-east-2 | Ohio, United States of America | 
| use2-az3 | us-east-2 | Ohio, United States of America | 
| usw1-az1 | us-west-1  † | California, United States of America | 
| usw1-az2 | us-west-1  † | California, United States of America | 
| usw1-az3 | us-west-1  † | California, United States of America | 
| usw2-az1 | us-west-2 | Oregon, United States of America | 
| usw2-az2 | us-west-2 | Oregon, United States of America | 
| usw2-az3 | us-west-2 | Oregon, United States of America | 
| usw2-az4 | us-west-2 | Oregon, United States of America | 
| cac1-az1 | ca-central-1 | Canada | 
| cac1-az2 | ca-central-1 | Canada | 
| cac1-az4 | ca-central-1 | Canada | 
| caw1-az1 | ca-west-1 | Canada | 
| caw1-az2 | ca-west-1 | Canada | 
| caw1-az3 | ca-west-1 | Canada | 
| mxc1-az1 | mx-central-1 | Mexico | 
| mxc1-az2 | mx-central-1 | Mexico | 
| mxc1-az3 | mx-central-1 | Mexico | 

† Newer accounts can access two Availability Zones in US West (N. California).

## Africa
<a name="zones-africa"></a>

The following table lists the Availability Zones in Africa.


| AZ ID | Region | Geography | 
| --- | --- | --- | 
| afs1-az1 | af-south-1 | South Africa | 
| afs1-az2 | af-south-1 | South Africa | 
| afs1-az3 | af-south-1 | South Africa | 

## Asia Pacific
<a name="zones-asia-pacific"></a>

The following table lists the Asia Pacific Availability Zones.


| AZ ID | Region | Geography | 
| --- | --- | --- | 
| ape1-az1 | ap-east-1 | Hong Kong | 
| ape1-az2 | ap-east-1 | Hong Kong | 
| ape1-az3 | ap-east-1 | Hong Kong | 
| ape2-az1 | ap-east-2 | Taiwan | 
| ape2-az2 | ap-east-2 | Taiwan | 
| ape2-az3 | ap-east-2 | Taiwan | 
| apne1-az1 | ap-northeast-1 | Japan | 
| apne1-az2 | ap-northeast-1 | Japan | 
| apne1-az3 | ap-northeast-1 | Japan | 
| apne1-az4 | ap-northeast-1 | Japan | 
| apne2-az1 | ap-northeast-2 | South Korea | 
| apne2-az2 | ap-northeast-2 | South Korea | 
| apne2-az3 | ap-northeast-2 | South Korea | 
| apne2-az4 | ap-northeast-2 | South Korea | 
| apne3-az1 | ap-northeast-3 | Japan | 
| apne3-az2 | ap-northeast-3 | Japan | 
| apne3-az3 | ap-northeast-3 | Japan | 
| aps1-az1 | ap-south-1 | India | 
| aps1-az2 | ap-south-1 | India | 
| aps1-az3 | ap-south-1 | India | 
| aps2-az1 | ap-south-2 | India | 
| aps2-az2 | ap-south-2 | India | 
| aps2-az3 | ap-south-2 | India | 
| apse1-az1 | ap-southeast-1 | Singapore | 
| apse1-az2 | ap-southeast-1 | Singapore | 
| apse1-az3 | ap-southeast-1 | Singapore | 
| apse2-az1 | ap-southeast-2 | Australia | 
| apse2-az2 | ap-southeast-2 | Australia | 
| apse2-az3 | ap-southeast-2 | Australia | 
| apse3-az1 | ap-southeast-3 | Indonesia | 
| apse3-az2 | ap-southeast-3 | Indonesia | 
| apse3-az3 | ap-southeast-3 | Indonesia | 
| apse4-az1 | ap-southeast-4 | Australia | 
| apse4-az2 | ap-southeast-4 | Australia | 
| apse4-az3 | ap-southeast-4 | Australia | 
| apse5-az1 | ap-southeast-5 | Malaysia | 
| apse5-az2 | ap-southeast-5 | Malaysia | 
| apse5-az3 | ap-southeast-5 | Malaysia | 
| apse6-az1 | ap-southeast-6 | New Zealand | 
| apse6-az2 | ap-southeast-6 | New Zealand | 
| apse6-az3 | ap-southeast-6 | New Zealand | 
| apse7-az1 | ap-southeast-7 | Thailand | 
| apse7-az2 | ap-southeast-7 | Thailand | 
| apse7-az3 | ap-southeast-7 | Thailand | 

## Europe
<a name="zones-europe"></a>

The following table lists the Availability Zones in Europe.


| AZ ID | Region | Geography | 
| --- | --- | --- | 
| euc1-az1 | eu-central-1 | Germany | 
| euc1-az2 | eu-central-1 | Germany | 
| euc1-az3 | eu-central-1 | Germany | 
| euc2-az1 | eu-central-2 | Switzerland | 
| euc2-az2 | eu-central-2 | Switzerland | 
| euc2-az3 | eu-central-2 | Switzerland | 
| eun1-az1 | eu-north-1 | Sweden | 
| eun1-az2 | eu-north-1 | Sweden | 
| eun1-az3 | eu-north-1 | Sweden | 
| eus1-az1 | eu-south-1 | Italy | 
| eus1-az2 | eu-south-1 | Italy | 
| eus1-az3 | eu-south-1 | Italy | 
| eus2-az1 | eu-south-2 | Spain | 
| eus2-az2 | eu-south-2 | Spain | 
| eus2-az3 | eu-south-2 | Spain | 
| euw1-az1 | eu-west-1 | Ireland | 
| euw1-az2 | eu-west-1 | Ireland | 
| euw1-az3 | eu-west-1 | Ireland | 
| euw2-az1 | eu-west-2 | United Kingdom | 
| euw2-az2 | eu-west-2 | United Kingdom | 
| euw2-az3 | eu-west-2 | United Kingdom | 
| euw2-az4 | eu-west-2 | United Kingdom | 
| euw3-az1 | eu-west-3 | France | 
| euw3-az2 | eu-west-3 | France | 
| euw3-az3 | eu-west-3 | France | 

## Middle East
<a name="zones-middle-east"></a>

The following table lists the Availability Zones in the Middle East.


| AZ ID | Region | Geography | 
| --- | --- | --- | 
| ilc1-az1 | il-central-1 | Israel | 
| ilc1-az2 | il-central-1 | Israel | 
| ilc1-az3 | il-central-1 | Israel | 
| mec1-az1 | me-central-1 | United Arab Emirates | 
| mec1-az2 | me-central-1 | United Arab Emirates | 
| mec1-az3 | me-central-1 | United Arab Emirates | 
| mes1-az1 | me-south-1 | Bahrain | 
| mes1-az2 | me-south-1 | Bahrain | 
| mes1-az3 | me-south-1 | Bahrain | 

## South America
<a name="zones-south-america"></a>

The following table lists the Availability Zones in South America.


| AZ ID | Region | Geography | 
| --- | --- | --- | 
| sae1-az1 | sa-east-1 | Brazil | 
| sae1-az2 | sa-east-1 | Brazil | 
| sae1-az3 | sa-east-1 | Brazil | 

## Constrained Availability Zones
<a name="constrained-zones"></a>

As Availability Zones grow over time, our ability to expand them can become constrained. If this happens, we might restrict you from creating zonal resources in a constrained Availability Zone, unless you already have resources in that Availability Zone. Eventually, we might also remove the constrained Availability Zone from the list of Availability Zones for new accounts. Therefore, your account might have a different number of available Availability Zones in a Region than another account does.

## View Availability Zone information
<a name="zones-example-commands"></a>

You can list the Availability Zones for your account and describe a single Availability Zone, including the AZ ID for each Availability Zone.

------
#### [ Console ]

**To view AZ IDs in the console**

1. Open the [AWS Global View console](https://console.aws.amazon.com/awsglobalview/home#RegionsAndZones).

1. On the **Regions** tab, select a Region, and then choose **View details**.

1. On the **Zones** tab, find the rows with a **Zone type** of **Availability zone**. The **Zone ID** column shows the AZ ID for each Availability Zone.

------
#### [ AWS CLI ]

**To list the Availability Zones in a Region**  
Use the following [describe-availability-zones](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-availability-zones.html) command. To include any Local Zones and Wavelength Zones that are opted in for your account, omit the `--filters` option.

```
aws ec2 describe-availability-zones \
  --filters Name=zone-type,Values=availability-zone \
  --region {{us-east-2}} \
  --query "AvailabilityZones[].{ZoneName:ZoneName,ZoneId:ZoneId}"
```

The following is example output for the US East (Ohio) Region.

```
[
    {
        "ZoneName": "us-east-2a",
        "ZoneId": "use2-az1"
    },
    {
        "ZoneName": "us-east-2b",
        "ZoneId": "use2-az2"
    },
    {
        "ZoneName": "us-east-2c",
        "ZoneId": "use2-az3"
    }
]
```

**To describe an Availability Zone**  
To view the details of a single Availability Zone, use the following [describe-availability-zones](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-availability-zones.html) command.

```
aws ec2 describe-availability-zones \
  --zone-name {{us-east-2a}} \
  --region {{us-east-2}}
```

The following is example output for `us-east-2a` in the US East (Ohio) Region.

```
{
    "AvailabilityZones": [
        {
            "OptInStatus": "opt-in-not-required",
            "Messages": [],
            "RegionName": "us-east-2",
            "ZoneName": "us-east-2a",
            "ZoneId": "use2-az1",
            "GroupName": "us-east-2-zg-1",
            "NetworkBorderGroup": "us-east-2",
            "ZoneType": "availability-zone",
            "GroupLongName": "US East (Ohio) 1",
            "Geography": [
                {
                    "Name": "United States of America"
                }
            ],
            "SubGeography": [
                {
                    "Name": "Ohio"
                }
            ],
            "State": "available"
        }
    ]
}
```

------
#### [ PowerShell ]

**To list the Availability Zones in a Region**  
Use the following [Get-EC2AvailabilityZone](https://docs.aws.amazon.com/powershell/latest/reference/items/Get-EC2AvailabilityZone.html) command. To include any Local Zones and Wavelength Zones that are opted in for your account, omit the `-Filter` parameter.

```
Get-EC2AvailabilityZone `
    -Filter @{Name="zone-type";Values="availability-zone"} `
    -Region {{us-east-2}} |
Select-Object ZoneName, ZoneId
```

The following is example output for the US East (Ohio) Region.

```
ZoneName   ZoneId
--------   ------
us-east-2a use2-az1
us-east-2b use2-az2
us-east-2c use2-az3
```

**To describe an Availability Zone**  
To view the details of a single Availability Zone, use the following [Get-EC2AvailabilityZone](https://docs.aws.amazon.com/powershell/latest/reference/items/Get-EC2AvailabilityZone.html) command.

```
Get-EC2AvailabilityZone -ZoneName {{us-east-2a}} -Region {{us-east-2}}
```

The following is example output for `us-east-2a` in the US East (Ohio) Region.

```
Geography          : {United States of America}
GroupLongName      : US East (Ohio) 1
GroupName          : us-east-2-zg-1
Messages           :
NetworkBorderGroup : us-east-2
OptInStatus        : opt-in-not-required
ParentZoneId       :
ParentZoneName     :
RegionName         : us-east-2
State              : available
SubGeography       : {Ohio}
ZoneId             : use2-az1
ZoneName           : us-east-2a
ZoneType           : availability-zone
```

------