import os
import logging
from datetime import datetime
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class FlagmanDistributor:
    def __init__(self):
        # Equipment pools for each area
        self.equipment_pools = {
            'GIS + MB': ['Cocklain', 'Bobcut', 'JCB', 'Compactor', 'Excavator', 'Hydra', 'Mini Roller', 'Trailer', 'Tough Rider', 'Roller', 'DCM'],
            'Chiller Area': ['JCB', 'Roller', 'Compactor', 'Tough Rider', 'Bobcut', 'DCM', 'Excavator', 'Hydra', 'Mini Roller'],
            'SSD': ['Hydra', 'JCB', 'Cocklain', 'Unicrane', 'Excavator', 'Main Lift', 'Compactor'],
            'Gate': ['Trailer', 'Tough Rider', 'Excavator', 'Roller', 'JCB', 'Hydra', 'Compactor'],
            'NCC Office': ['Hydra', 'Main Lift', 'Bobcut', 'Compactor', 'JCB', 'Cocklain', 'Roller'],
            'Store': ['Assigned'],
            'Supervisors': ['General Area']
        }
        
        # Priority weights for distribution (higher = more priority)
        self.area_priorities = {
            'GIS + MB': 8,
            'Chiller Area': 6,
            'SSD': 5,
            'Gate': 4,
            'NCC Office': 4,
            'Store': 2,
            'Supervisors': 1
        }

    def distribute_personnel(self, total_personnel):
        if total_personnel < 7:  # Minimum one person per area
            return None
            
        # Calculate base distribution based on priorities
        total_priority = sum(self.area_priorities.values())
        distribution = {}
        allocated = 0
        
        # First pass - allocate based on priority ratios
        for area, priority in self.area_priorities.items():
            if area == 'Supervisors':
                continue  # Handle supervisors separately
            count = max(1, int((priority / total_priority) * (total_personnel - 1)))  # -1 for supervisor
            distribution[area] = count
            allocated += count
        
        # Always have 1 supervisor
        distribution['Supervisors'] = 1
        allocated += 1
        
        # Distribute remaining personnel
        remaining = total_personnel - allocated
        areas = list(self.area_priorities.keys())[:-1]  # Exclude supervisors
        
        while remaining > 0:
            # Add to areas with highest priority first
            for area in sorted(areas, key=lambda x: self.area_priorities[x], reverse=True):
                if remaining > 0:
                    distribution[area] += 1
                    remaining -= 1
        
        # Handle negative remaining (over-allocation)
        while remaining < 0:
            # Remove from areas with lowest priority first
            for area in sorted(areas, key=lambda x: self.area_priorities[x]):
                if distribution[area] > 1 and remaining < 0:
                    distribution[area] -= 1
                    remaining += 1
        
        return distribution

    def get_equipment_assignments(self, area, count):
        if area == 'Supervisors':
            return ['General Area']
        
        equipment_list = self.equipment_pools[area].copy()
        assignments = []
        
        # For Store area, always assign "Assigned"
        if area == 'Store':
            return [f'Assigned x{count}'] if count > 1 else ['Assigned']
        
        # Shuffle for variety
        random.shuffle(equipment_list)
        
        # Assign equipment, allowing duplicates with count notation
        equipment_counts = {}
        for i in range(count):
            equipment = equipment_list[i % len(equipment_list)]
            equipment_counts[equipment] = equipment_counts.get(equipment, 0) + 1
        
        # Format assignments
        for equipment, eq_count in equipment_counts.items():
            if eq_count > 1:
                assignments.append(f'{equipment} x{eq_count}')
            else:
                assignments.append(equipment)
        
        return assignments

    def generate_report(self, total_personnel):
        distribution = self.distribute_personnel(total_personnel)
        if not distribution:
            return " Minimum 7 personnel required for distribution."
        
        current_date = datetime.now().strftime("%d-%m-%Y")
        
        report = f"*Flagman Distribution Report*\n"
        report += f"*Date :- {current_date}*\n\n"
        
        flagmen_count = total_personnel - distribution['Supervisors']
        
        # Generate assignments for each area
        for area in ['GIS + MB', 'Chiller Area', 'SSD', 'Gate', 'NCC Office', 'Store', 'Supervisors']:
            count = distribution[area]
            assignments = self.get_equipment_assignments(area, count)
            assignments_str = ', '.join(assignments)
            report += f"*{area} ({count})* – {assignments_str}\n"
        
        report += f"\n*Total Personnel: {total_personnel} ({flagmen_count} Flagmen + {distribution['Supervisors']} Supervisors)*"
        
        return report

# Initialize the distributor
distributor = FlagmanDistributor()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = """
🚧 *Flagman Distribution Bot* 🚧

Welcome! I can generate daily flagman distribution reports.

*Commands:*
• `/report <number>` - Generate distribution report
  Example: `/report 30`

• `/help` - Show this help message

*Note:* Minimum 7 personnel required for distribution.
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
*How to use:*

1️⃣ Type `/report` followed by the number of personnel
   Example: `/report 25`

2️⃣ The bot will generate a distribution report with:
   • Current date
   • Personnel assigned to each area
   • Equipment assignments
   • Total count breakdown

*Areas covered:*
• GIS + MB
• Chiller Area  
• SSD
• Gate
• NCC Office
• Store
• Supervisors

*Minimum personnel required: 7*
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send the flagman distribution report."""
    try:
        # Check if personnel count is provided
        if not context.args:
            await update.message.reply_text(
                " Please provide personnel count.\n\n*Usage:* `/report <number>`\n*Example:* `/report 30`",
                parse_mode='Markdown'
            )
            return
        
        # Parse personnel count
        try:
            personnel_count = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                " Please provide a valid number.\n\n*Example:* `/report 30`",
                parse_mode='Markdown'
            )
            return
        
        # Validate personnel count
        if personnel_count < 1:
            await update.message.reply_text(
                " Personnel count must be at least 1.",
                parse_mode='Markdown'
            )
            return
        
        if personnel_count > 200:
            await update.message.reply_text(
                " Personnel count seems too high. Maximum allowed: 200.",
                parse_mode='Markdown'
            )
            return
        
        # Generate report
        report = distributor.generate_report(personnel_count)
        
        # Send report
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in report_command: {e}")
        await update.message.reply_text(
            " An error occurred while generating the report. Please try again.",
            parse_mode='Markdown'
        )

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands."""
    await update.message.reply_text(
        " Unknown command. Type `/help` for available commands.",
        parse_mode='Markdown'
    )

def main() -> None:
    """Start the bot."""
    # Get bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("report", report_command))
    
    # Log bot startup
    logger.info("Bot starting...")
    
    # Run the bot
    port = int(os.environ.get("PORT", 8080))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,
        webhook_url=f"https://your-app-name.onrender.com/{token}"
    )

if __name__ == '__main__':
    main()