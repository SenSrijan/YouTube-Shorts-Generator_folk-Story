from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, User, SubscriptionPlan, PaymentHistory
import stripe
from datetime import datetime, timedelta
import json

sub_bp = Blueprint('subscription', __name__)

def init_stripe(app):
    stripe.api_key = app.config['STRIPE_SECRET_KEY']

@sub_bp.route('/plans')
@login_required
def plans():
    """Display available subscription plans"""
    active_plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    return render_template('subscription/plans.html', 
                           plans=active_plans, 
                           current_plan=current_user.subscription_tier)


@sub_bp.route('/checkout/<plan_name>')
@login_required
def checkout(plan_name):
    """Create a Stripe checkout session for the selected plan"""
    plan = SubscriptionPlan.query.filter_by(name=plan_name, is_active=True).first()
    
    if not plan:
        flash('Selected plan is not available.', 'error')
        return redirect(url_for('subscription.plans'))
    
    # Check if user is already on this plan
    if current_user.subscription_tier == plan_name and current_user.subscription_status == 'active':
        flash('You are already subscribed to this plan.', 'info')
        return redirect(url_for('dashboard.index'))
    
    try:
        # Create or retrieve the Stripe customer
        if current_user.stripe_customer_id:
            customer = stripe.Customer.retrieve(current_user.stripe_customer_id)
        else:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={'user_id': current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('subscription.success', _external=True) + 
                        f'?session_id={{CHECKOUT_SESSION_ID}}&plan={plan_name}',
            cancel_url=url_for('subscription.plans', _external=True),
            metadata={
                'user_id': current_user.id,
                'plan': plan_name
            }
        )
        
        return redirect(checkout_session.url)
        
    except Exception as e:
        current_app.logger.error(f"Stripe checkout error: {str(e)}")
        flash('An error occurred during checkout. Please try again.', 'error')
        return redirect(url_for('subscription.plans'))


@sub_bp.route('/success')
@login_required
def success():
    """Handle successful checkout"""
    session_id = request.args.get('session_id')
    plan_name = request.args.get('plan')
    
    if not session_id or not plan_name:
        flash('Invalid request.', 'error')
        return redirect(url_for('dashboard.index'))
    
    try:
        # Verify the checkout session
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.customer != current_user.stripe_customer_id:
            flash('Invalid checkout session.', 'error')
            return redirect(url_for('dashboard.index'))
        
        # Update user's subscription
        current_user.subscription_tier = plan_name
        current_user.subscription_status = 'active'
        current_user.subscription_expiry = datetime.utcnow() + timedelta(days=30)  # 30-day subscription
        
        # Reset usage counters
        current_user.monthly_generations = 0
        
        # Record payment
        payment = PaymentHistory(
            user_id=current_user.id,
            stripe_payment_id=session.payment_intent,
            amount=session.amount_total / 100,  # Convert from cents
            status='succeeded',
            subscription_plan=plan_name
        )
        
        db.session.add(payment)
        db.session.commit()
        
        flash(f'You have successfully subscribed to the {plan_name.capitalize()} plan!', 'success')
        return redirect(url_for('dashboard.index'))
        
    except Exception as e:
        current_app.logger.error(f"Subscription success error: {str(e)}")
        flash('An error occurred while processing your subscription. Please contact support.', 'error')
        return redirect(url_for('dashboard.index'))


@sub_bp.route('/cancel', methods=['POST'])
@login_required
def cancel():
    """Cancel subscription"""
    if current_user.subscription_tier == 'free':
        flash('You are not currently subscribed to any plan.', 'info')
        return redirect(url_for('dashboard.index'))
    
    try:
        # Get active subscriptions for the customer
        subscriptions = stripe.Subscription.list(
            customer=current_user.stripe_customer_id,
            status='active'
        )
        
        if subscriptions.data:
            # Cancel the subscription at period end
            for subscription in subscriptions.data:
                stripe.Subscription.modify(
                    subscription.id,
                    cancel_at_period_end=True
                )
        
        # Update user record
        current_user.subscription_status = 'canceled'
        db.session.commit()
        
        flash('Your subscription has been canceled and will end at the current billing period.', 'info')
        return redirect(url_for('dashboard.subscription'))
        
    except Exception as e:
        current_app.logger.error(f"Subscription cancellation error: {str(e)}")
        flash('An error occurred while canceling your subscription. Please try again.', 'error')
        return redirect(url_for('dashboard.subscription'))


@sub_bp.route('/webhook', methods=['POST'])
def webhook():
    """Stripe webhook handler for subscription events"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    if not sig_header:
        return jsonify({'error': 'Missing signature header'}), 400
    
    # Verify the event
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle specific events
    if event['type'] == 'invoice.payment_succeeded':
        handle_payment_succeeded(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    
    return jsonify({'success': True}), 200


def handle_payment_succeeded(invoice):
    """Process successful subscription payment"""
    stripe_customer_id = invoice.get('customer')
    user = User.query.filter_by(stripe_customer_id=stripe_customer_id).first()
    
    if not user:
        current_app.logger.error(f"Payment succeeded for unknown customer: {stripe_customer_id}")
        return
    
    # Update subscription expiry
    user.subscription_expiry = datetime.utcnow() + timedelta(days=30)
    user.subscription_status = 'active'
    
    # Record payment
    subscription_id = invoice.get('subscription')
    subscription = stripe.Subscription.retrieve(subscription_id)
    plan_id = subscription.items.data[0].price.id if subscription.items.data else None
    
    if plan_id:
        plan = SubscriptionPlan.query.filter_by(stripe_price_id=plan_id).first()
        plan_name = plan.name if plan else 'unknown'
    else:
        plan_name = 'unknown'
    
    payment = PaymentHistory(
        user_id=user.id,
        stripe_payment_id=invoice.get('id'),
        amount=invoice.get('amount_paid') / 100,  # Convert from cents
        status='succeeded',
        subscription_plan=plan_name
    )
    
    db.session.add(payment)
    db.session.commit()
    current_app.logger.info(f"Payment succeeded for user {user.id}, plan {plan_name}")


def handle_payment_failed(invoice):
    """Process failed subscription payment"""
    stripe_customer_id = invoice.get('customer')
    user = User.query.filter_by(stripe_customer_id=stripe_customer_id).first()
    
    if not user:
        current_app.logger.error(f"Payment failed for unknown customer: {stripe_customer_id}")
        return
    
    # Update subscription status
    user.subscription_status = 'payment_failed'
    
    # Record failed payment
    payment = PaymentHistory(
        user_id=user.id,
        stripe_payment_id=invoice.get('id'),
        amount=invoice.get('amount_due') / 100,  # Convert from cents
        status='failed',
        subscription_plan=user.subscription_tier
    )
    
    db.session.add(payment)
    db.session.commit()
    current_app.logger.info(f"Payment failed for user {user.id}")


def handle_subscription_deleted(subscription):
    """Process subscription cancellation/expiration"""
    stripe_customer_id = subscription.get('customer')
    user = User.query.filter_by(stripe_customer_id=stripe_customer_id).first()
    
    if not user:
        current_app.logger.error(f"Subscription deleted for unknown customer: {stripe_customer_id}")
        return
    
    # Downgrade to free tier
    user.subscription_tier = 'free'
    user.subscription_status = 'expired'
    user.subscription_expiry = None
    
    db.session.commit()
    current_app.logger.info(f"Subscription ended for user {user.id}")


def initialize_plans():
    """Create or update subscription plans in the database"""
    plans = [
        {
            'name': 'free',
            'stripe_price_id': 'free_tier',  # Placeholder, not used with Stripe
            'monthly_generations': 3,
            'price_monthly': 0.00,
            'features': json.dumps([
                'Generate up to 3 YouTube Shorts per month',
                'Basic story generation',
                'Standard voiceover quality',
                'Web access only'
            ])
        },
        {
            'name': 'basic',
            'stripe_price_id': 'price_1234',  # Replace with actual Stripe price ID
            'monthly_generations': 30,
            'price_monthly': 9.99,
            'features': json.dumps([
                'Generate up to 30 YouTube Shorts per month',
                'Advanced story generation',
                'Premium voiceover quality',
                'API access with 100 daily requests',
                'Download in multiple formats'
            ])
        },
        {
            'name': 'premium',
            'stripe_price_id': 'price_5678',  # Replace with actual Stripe price ID
            'monthly_generations': 999999,  # Unlimited for practical purposes
            'price_monthly': 29.99,
            'features': json.dumps([
                'Unlimited YouTube Shorts generation',
                'Priority processing',
                'Highest quality voiceover',
                'Advanced API access with 1000 daily requests',
                'Team collaboration features',
                'White-label downloads',
                'Priority support'
            ])
        }
    ]
    
    for plan_data in plans:
        existing_plan = SubscriptionPlan.query.filter_by(name=plan_data['name']).first()
        
        if existing_plan:
            # Update existing plan
            for key, value in plan_data.items():
                setattr(existing_plan, key, value)
        else:
            # Create new plan
            new_plan = SubscriptionPlan(**plan_data)
            db.session.add(new_plan)
    
    db.session.commit()