# IronHub Template System - User Guide

## 📚 Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Templates](#creating-templates)
3. [Using Templates](#using-templates)
4. [Managing Templates](#managing-templates)
5. [Excel Migration](#excel-migration)
6. [Analytics & Insights](#analytics--insights)
7. [Mobile Features](#mobile-features)
8. [Troubleshooting](#troubleshooting)

---

## 🚀 Getting Started

### What is the Template System?

The IronHub Template System allows you to:
- Create custom workout templates with exercises, sets, reps, and rest periods
- Generate professional PDFs for your clients
- Track template usage and performance
- Migrate existing Excel templates to the new system
- Share templates with your gym or make them public

### First Steps

1. **Log in** to your IronHub account
2. **Navigate** to the Templates section
3. **Browse** existing templates or create your own
4. **Start** using templates with your clients

---

## 🎨 Creating Templates

### Template Builder Overview

The template builder consists of several sections:

#### 1. Basic Information
- **Name**: Template name (required)
- **Description**: Detailed description
- **Category**: Exercise category (strength, cardio, flexibility, etc.)
- **Days per Week**: How many days this routine covers
- **Tags**: Keywords for easy searching

#### 2. Layout Configuration
- **Page Size**: A4, A3, Letter
- **Orientation**: Portrait or Landscape
- **Margins**: Adjust spacing around content
- **Columns**: Layout columns for exercises

#### 3. Sections

Templates are built using sections. Common sections include:

##### Header Section
- Gym name and logo
- Client information
- Trainer name
- Date and routine name

##### Exercise Table Section
- Exercise names and details
- Sets, reps, and rest periods
- Exercise notes and instructions
- Progress tracking areas

##### Footer Section
- Signature lines
- Additional notes
- Disclaimer text

### Step-by-Step Template Creation

#### Step 1: Create New Template

1. Click **"Create Template"** button
2. Fill in basic information:
   ```
   Name: "Full Body Strength"
   Description: "Complete full body workout for beginners"
   Category: "Strength"
   Days per Week: 3
   Tags: "beginner, full-body, strength"
   ```

#### Step 2: Configure Layout

1. Choose page settings:
   ```
   Page Size: A4
   Orientation: Portrait
   Margins: 20mm all sides
   ```

2. Select styling options:
   ```
   Font: Arial
   Font Size: 12pt
   Primary Color: #000000 (Black)
   ```

#### Step 3: Add Sections

1. **Add Header Section**
   - Enable gym name display
   - Include client name field
   - Add trainer name
   - Show current date

2. **Add Exercise Table**
   - Set table columns: Exercise, Sets, Reps, Rest, Notes
   - Add exercises:
     ```
     Exercise 1: Squats
     - Sets: 3
     - Reps: 12
     - Rest: 90s
     - Notes: "Keep back straight"
     
     Exercise 2: Push-ups
     - Sets: 3
     - Reps: 10
     - Rest: 60s
     - Notes: "Full range of motion"
     ```

3. **Add Footer Section**
   - Enable signature line
   - Add disclaimer text
   - Include date field

#### Step 4: Preview and Save

1. Click **"Preview"** to see how it will look
2. Review all sections and content
3. Click **"Save Template"** when satisfied

### Template Variables

Use variables to make templates dynamic:

#### Common Variables
- `{{gym_name}}`: Your gym name
- `{{client_name}}`: Client's name
- `{{trainer_name}}`: Trainer's name
- `{{date}}`: Current date
- `{{time}}`: Current time

#### Custom Variables
Create your own variables for personalized templates:
```
{{client_goal}}: Client's fitness goal
{{experience_level}}: Beginner/Intermediate/Advanced
{{medical_notes}}: Important medical considerations
```

### Template Best Practices

#### Do's
✅ Use clear, descriptive names
✅ Include detailed exercise instructions
✅ Add appropriate rest periods
✅ Use consistent formatting
✅ Test preview before saving

#### Don'ts
❌ Don't overcrowd the page
❌ Don't use too many different fonts
❌ Don't forget important safety notes
❌ Don't make exercises too complex
❌ Don't skip the preview step

---

## 📋 Using Templates

### Assigning Templates to Clients

#### Method 1: From Template Library

1. **Browse** templates in the library
2. **Filter** by category or search by name
3. **Select** the template you want to use
4. **Click** "Use Template"
5. **Fill in** client information
6. **Generate** PDF or save to client profile

#### Method 2: From Client Profile

1. **Navigate** to client's profile
2. **Click** "Assign Template"
3. **Choose** from available templates
4. **Customize** if needed
5. **Save** assignment

### Generating PDFs

#### Quick PDF Generation

1. **Select** template
2. **Click** "Generate PDF"
3. **Choose** options:
   - Quality: Standard/High
   - Include watermark: Yes/No
   - Add metadata: Yes/No
4. **Download** PDF file

#### Advanced PDF Options

For professional PDFs, use advanced options:

```bash
# High quality for printing
Quality: High (300 DPI)
Include: Watermark, Metadata, QR Code
Format: A4, Portrait
Color: Full Color
```

### Template Customization

#### Before Generation

You can customize templates before generating PDFs:

1. **Edit** exercise details
2. **Modify** sets/reps for client level
3. **Add** client-specific notes
4. **Adjust** rest periods
5. **Include** progression tracking

#### Saving Customizations

Save customized versions as new templates:
1. **Click** "Save As New Template"
2. **Enter** new name
3. **Choose** to make public or private
4. **Add** appropriate tags

---

## 📊 Managing Templates

### Template Organization

#### Categories

Organize templates by categories:
- **Strength**: Weight training, resistance exercises
- **Cardio**: Cardiovascular workouts
- **Flexibility**: Stretching and mobility
- **Sports**: Sport-specific training
- **Rehabilitation**: Injury recovery exercises
- **Beginner**: Entry-level workouts
- **Advanced**: High-intensity training

#### Tags and Labels

Use tags for better organization:
```
#strength #lower-body #upper-body #core #cardio
#beginner #intermediate #advanced
#30min #45min #60min
#equipment #no-equipment #dumbbells #barbell
```

### Template Versions

#### Version History

Every template change creates a new version:
- **Version 1.0**: Initial creation
- **Version 1.1**: First modification
- **Version 2.0**: Major update

#### Managing Versions

1. **View** version history in template details
2. **Compare** different versions
3. **Restore** previous versions if needed
4. **Archive** old versions to keep library clean

### Sharing Templates

#### Private Templates
- Only visible to you
- Can be assigned to your clients
- Not searchable by others

#### Gym Templates
- Visible to all trainers in your gym
- Can be used by gym members
- Require gym admin approval

#### Public Templates
- Available to all IronHub users
- Can be rated and reviewed
- Help build your reputation

### Template Analytics

#### Usage Metrics

Track template performance:
- **Total Uses**: How many times used
- **Unique Users**: Different clients who used it
- **Monthly Usage**: Usage trends over time
- **Client Progress**: Results achieved

#### Rating System

Clients and trainers can rate templates:
- ⭐⭐⭐⭐⭐ Excellent
- ⭐⭐⭐⭐ Good
- ⭐⭐⭐ Average
- ⭐⭐ Below Average
- ⭐ Poor

#### Improvement Insights

Use analytics to improve templates:
1. **Identify** most popular exercises
2. **Analyze** usage patterns
3. **Update** based on feedback
4. **Create** variations for different levels

---

## 📈 Excel Migration

### Preparing Excel Files

#### Supported Formats

Your Excel files should have this structure:

```
| Exercise    | Sets | Reps  | Rest  | Notes          |
|-------------|------|-------|-------|----------------|
| Squats      | 3    | 12    | 90s   | Keep back straight |
| Push-ups    | 3    | 10    | 60s   | Full range      |
| Pull-ups    | 3    | 8     | 60s   | Wide grip       |
```

#### Configuration Rows (Optional)

Add configuration at the top:
```
| Name        | My Workout Template      |
| Description | Full body strength routine |
| Category    | Strength                 |
| Days        | 3                        |
```

### Migration Process

#### Step 1: Upload Excel File

1. **Go to** Migration section
2. **Click** "Upload Excel File"
3. **Select** your Excel file
4. **Enter** template information:
   ```
   Template Name: "Migrated from Excel"
   Description: "Converted from existing spreadsheet"
   Category: "Strength"
   ```

#### Step 2: Preview Migration

The system will show:
- **Detected exercises**: List of found exercises
- **Template structure**: How it will be organized
- **Estimated sections**: Number of sections created
- **Migration complexity**: Easy/Medium/Hard

#### Step 3: Review and Confirm

1. **Check** detected exercises
2. **Verify** template structure
3. **Edit** if necessary
4. **Confirm** migration

#### Step 4: Post-Migration

After migration:
1. **Review** the created template
2. **Test** PDF generation
3. **Edit** styling if needed
4. **Save** final version

### Batch Migration

#### Multiple Files

Migrate multiple Excel files at once:

1. **Select** multiple Excel files
2. **Choose** default settings
3. **Start** batch migration
4. **Monitor** progress
5. **Review** results

#### Migration Reports

Get detailed reports:
- **Success rate**: Percentage of successful migrations
- **Errors encountered**: Issues that need fixing
- **Recommendations**: Suggestions for improvement

---

## 📊 Analytics & Insights

### Dashboard Overview

Your analytics dashboard shows:

#### Key Metrics
- **Total Templates**: Number of templates created
- **Active Templates**: Currently used templates
- **Client Usage**: How many clients use your templates
- **Popular Templates**: Most used templates

#### Usage Trends
- **Daily/Weekly/Monthly** usage graphs
- **Seasonal patterns** in template usage
- **Client engagement** metrics
- **Template performance** over time

### Client Progress Tracking

#### Individual Client Analytics

For each client:
- **Templates used**: Which templates they've used
- **Progress metrics**: Strength gains, endurance improvements
- **Adherence rate**: How consistently they follow routines
- **Feedback**: Client ratings and comments

#### Progress Reports

Generate progress reports:
1. **Select** client and time period
2. **Choose** metrics to include
3. **Generate** PDF report
4. **Share** with client

### Template Performance

#### Best Performing Templates

Identify your most effective templates:
- **High usage** templates
- **High client satisfaction**
- **Good progress results**
- **Low dropout rates**

#### Optimization Opportunities

Find areas for improvement:
- **Unused templates**: Consider updating or removing
- **Low-rated templates**: Revise based on feedback
- **Complex templates**: Simplify for better adherence
- **Missing categories**: Create templates for gaps

---

## 📱 Mobile Features

### Mobile App Overview

The IronHub mobile app provides:
- **Template browsing** and searching
- **QR code scanning** for gym equipment
- **Workout tracking** and logging
- **Progress monitoring** on the go
- **Push notifications** for reminders

### Using Templates on Mobile

#### Accessing Templates

1. **Open** IronHub mobile app
2. **Navigate** to Templates section
3. **Browse** or search for templates
4. **Tap** to view details
5. **Start** workout when ready

#### QR Code Integration

Scan QR codes for:
- **Equipment setup**: Proper machine settings
- **Exercise form**: Video demonstrations
- **Weight tracking**: Automatic logging
- **Progress photos**: Visual progress tracking

#### Workout Tracking

During workouts:
- **Log sets and reps** as you complete them
- **Track rest periods** with built-in timer
- **Record weight used** for each exercise
- **Add notes** about how you felt
- **Take progress photos** if desired

### Mobile-Specific Features

#### Offline Mode

- **Download** templates for offline use
- **Track workouts** without internet
- **Sync** when connection restored
- **Access** basic exercise information

#### Notifications

Set up reminders for:
- **Workout days**: Time to exercise
- **Template updates**: New versions available
- **Client messages**: Trainer communications
- **Progress milestones**: Achievement celebrations

---

## 🔧 Troubleshooting

### Common Issues

#### Template Creation Problems

**Issue**: Template preview doesn't show correctly
**Solution**: 
1. Check all required fields are filled
2. Verify exercise data is complete
3. Try refreshing the page
4. Contact support if issue persists

**Issue**: PDF generation fails
**Solution**:
1. Check template has all required sections
2. Verify no special characters in exercise names
3. Try reducing template complexity
4. Use standard fonts and colors

#### Migration Issues

**Issue**: Excel file won't upload
**Solution**:
1. Check file is in .xlsx or .xls format
2. Verify file size is under 10MB
3. Ensure file is not password protected
4. Try saving as a new Excel file

**Issue**: Exercises not detected correctly
**Solution**:
1. Check column headers match expected format
2. Verify exercise names are in first column
3. Ensure no empty rows in exercise table
4. Use standard exercise naming

#### Performance Issues

**Issue**: Templates load slowly
**Solution**:
1. Check internet connection speed
2. Clear browser cache and cookies
3. Try using a different browser
4. Contact IT support if problem continues

**Issue**: Mobile app crashes
**Solution**:
1. Update to latest app version
2. Restart your device
3. Clear app cache
4. Reinstall app if necessary

### Getting Help

#### Support Channels

1. **In-App Help**: Tap the help icon in the app
2. **Email Support**: support@ironhub.com
3. **Phone Support**: 1-800-IRONHUB (Mon-Fri, 9AM-5PM EST)
4. **Live Chat**: Available on website during business hours

#### What to Include in Support Requests

When contacting support, please include:
- **Your account information**
- **Device and browser details**
- **Steps to reproduce the issue**
- **Screenshots if applicable**
- **Error messages received**

#### FAQ Section

Check our FAQ for quick answers:
- **Account management**: Password resets, profile updates
- **Template creation**: Common questions and tips
- **Billing and subscriptions**: Payment issues
- **Technical requirements**: System compatibility

### Best Practices

#### Regular Maintenance

Keep your account running smoothly:
- **Update** templates regularly
- **Archive** unused templates
- **Backup** important templates
- **Review** client progress monthly

#### Security

Protect your account:
- **Use strong passwords**
- **Enable two-factor authentication**
- **Log out** after each session
- **Report** suspicious activity

#### Data Management

Manage your data effectively:
- **Export** templates regularly
- **Backup** client progress data
- **Clean up** old files
- **Monitor** storage usage

---

## 📞 Additional Resources

### Training Materials

- **Video Tutorials**: Step-by-step guides
- **Webinars**: Live training sessions
- **Blog Articles**: Tips and best practices
- **Case Studies**: Success stories from other trainers

### Community

- **User Forum**: Connect with other trainers
- **Facebook Group**: Share tips and templates
- **LinkedIn Network**: Professional discussions
- **Annual Conference**: In-person networking

### Updates and Announcements

Stay informed about:
- **New features** and improvements
- **System maintenance** schedules
- **Policy changes** and updates
- **Educational opportunities**

---

*This user guide is updated regularly. Check for new versions quarterly.*

**Last Updated**: January 2024
**Version**: 1.0

For the most current information, visit our help center at help.ironhub.com
