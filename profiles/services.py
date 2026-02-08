"""
Profile services for business logic.
Follows Single Responsibility Principle - each service handles specific business logic.
"""

import os
from django.core.files.storage import default_storage
from django.utils import timezone
from .models import UserProfile, ProfileActivityLog


class ProfileService:
    """
    Service class for profile-related business logic.
    """
    
    @staticmethod
    def log_activity(profile, action, field_changed=None, old_value=None, new_value=None, metadata=None, request=None):
        """
        Log profile activity for audit purposes.
        """
        activity_data = {
            'profile': profile,
            'action': action,
            'field_changed': field_changed or '',
            'old_value': old_value or '',
            'new_value': new_value or '',
        }

        if metadata is None:
            metadata = {}

        # If old/new are provided, add a basic changes entry
        if field_changed and (old_value is not None or new_value is not None):
            metadata = {
                **metadata,
                'changes': [
                    {
                        'field': field_changed,
                        'old': old_value,
                        'new': new_value,
                    }
                ]
            }

        activity_data['metadata'] = metadata
        
        if request:
            activity_data.update({
                'ip_address': ProfileService.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],  
            })
        
        return ProfileActivityLog.objects.create(**activity_data)
        try:
            activity_data = {
                'profile': profile,
                'action': action,
                'field_changed': field_changed or '',
                'old_value': str(old_value) if old_value else '',
                'new_value': str(new_value) if new_value else '',
            }
            
            if request:
                activity_data.update({
                    'ip_address': ProfileService.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],  # Truncate long user agents
                })
            
            return ProfileActivityLog.objects.create(**activity_data)
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Warning: Failed to log profile activity: {e}")
            return None
    
    @staticmethod
    def get_client_ip(request):
        """
        Extract client IP address from request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    @staticmethod
    def remove_profile_picture(profile):
        """
        Safely remove profile picture file from storage.
        """
        if profile.profile_picture:
            try:
                # Delete the file from storage
                if default_storage.exists(profile.profile_picture.name):
                    default_storage.delete(profile.profile_picture.name)
            except Exception as e:
                # Log error but don't fail the operation
                print(f"Error removing profile picture: {e}")
    
    @staticmethod
    def get_completion_status(profile):
        """
        Calculate profile completion status and provide suggestions.
        """
        # Define field categories and their weights
        field_categories = {
            'personal': {
                'weight': 30,
                'fields': [
                    ('first_name', 'First Name'),
                    ('last_name', 'Last Name'),
                    ('phone_number', 'Phone Number'),
                    ('date_of_birth', 'Date of Birth'),
                ]
            },
            'address': {
                'weight': 20,
                'fields': [
                    ('address_line_1', 'Address'),
                    ('city', 'City'),
                    ('country', 'Country'),
                ]
            },
            'professional': {
                'weight': 30,
                'fields': [
                    ('job_title', 'Job Title'),
                    ('organization', 'Organization'),
                    ('icpau_registration_number', 'ICPAU Registration Number'),
                ]
            },
            'additional': {
                'weight': 20,
                'fields': [
                    ('bio', 'Professional Bio'),
                    ('profile_picture', 'Profile Picture'),
                    ('specializations', 'Specializations'),
                ]
            }
        }
        
        completion_data = {
            'overall_percentage': 0,
            'categories': {},
            'missing_fields': [],
            'suggestions': []
        }
        
        total_weighted_score = 0
        total_weight = 0
        
        for category_name, category_info in field_categories.items():
            filled_fields = 0
            total_fields = len(category_info['fields'])
            missing_in_category = []
            
            for field_name, field_label in category_info['fields']:
                field_value = getattr(profile, field_name, None)
                
                if field_value:
                    # Handle different field types
                    if hasattr(field_value, 'name'):  # File field
                        if field_value.name:
                            filled_fields += 1
                        else:
                            missing_in_category.append(field_label)
                    elif isinstance(field_value, str):
                        if field_value.strip():
                            filled_fields += 1
                        else:
                            missing_in_category.append(field_label)
                    else:
                        filled_fields += 1
                else:
                    missing_in_category.append(field_label)
            
            # Calculate category percentage
            category_percentage = (filled_fields / total_fields) * 100 if total_fields > 0 else 0
            
            completion_data['categories'][category_name] = {
                'percentage': round(category_percentage, 1),
                'filled_fields': filled_fields,
                'total_fields': total_fields,
                'missing_fields': missing_in_category
            }
            
            # Add to overall calculation
            weighted_score = (category_percentage / 100) * category_info['weight']
            total_weighted_score += weighted_score
            total_weight += category_info['weight']
            
            # Add missing fields to overall list
            completion_data['missing_fields'].extend(missing_in_category)
        
        # Calculate overall percentage
        completion_data['overall_percentage'] = round(
            (total_weighted_score / total_weight) * 100 if total_weight > 0 else 0,
            1
        )
        
        # Generate suggestions based on completion status
        completion_data['suggestions'] = ProfileService._generate_suggestions(
            completion_data['overall_percentage'],
            completion_data['categories']
        )
        
        return completion_data
    
    @staticmethod
    def _generate_suggestions(overall_percentage, categories):
        """
        Generate personalized suggestions for profile improvement.
        """
        suggestions = []
        
        if overall_percentage < 50:
            suggestions.append({
                'priority': 'high',
                'message': 'Complete your basic information to improve your profile visibility.',
                'action': 'Add missing personal and contact details'
            })
        
        # Category-specific suggestions
        for category_name, category_data in categories.items():
            if category_data['percentage'] < 70:
                if category_name == 'personal':
                    suggestions.append({
                        'priority': 'high',
                        'message': 'Add your personal information to help others connect with you.',
                        'action': f"Complete: {', '.join(category_data['missing_fields'][:3])}"
                    })
                elif category_name == 'professional':
                    suggestions.append({
                        'priority': 'medium',
                        'message': 'Showcase your professional background to build credibility.',
                        'action': f"Add: {', '.join(category_data['missing_fields'][:2])}"
                    })
                elif category_name == 'additional':
                    suggestions.append({
                        'priority': 'low',
                        'message': 'Enhance your profile with additional details.',
                        'action': f"Consider adding: {', '.join(category_data['missing_fields'][:2])}"
                    })
        
        # Profile picture specific suggestion
        if not any('Profile Picture' in cat['missing_fields'] for cat in categories.values()):
            pass  # Profile picture exists
        else:
            suggestions.append({
                'priority': 'medium',
                'message': 'Add a professional profile picture to make a great first impression.',
                'action': 'Upload a clear, professional headshot'
            })
        
        return suggestions[:5]  # Limit to top 5 suggestions


class ProfileValidationService:
    """
    Service for profile data validation and business rules.
    """
    
    @staticmethod
    def validate_icpau_number(icpau_number):
        """
        Validate ICPAU registration number format.
        """
        if not icpau_number:
            return True, ""
        
        # Basic format validation (adjust based on actual ICPAU format)
        if len(icpau_number) < 5:
            return False, "ICPAU registration number is too short"
        
        # Add more specific validation rules as needed
        return True, ""
    
    @staticmethod
    def validate_professional_info(job_title, organization, years_of_experience):
        """
        Validate professional information consistency.
        """
        errors = []
        
        if years_of_experience and years_of_experience > 50:
            errors.append("Years of experience seems unusually high")
        
        if job_title and not organization:
            errors.append("Organization is recommended when job title is provided")
        
        return len(errors) == 0, errors


class ProfileSearchService:
    """
    Service for profile search and filtering (for admin users).
    """
    
    @staticmethod
    def search_profiles(query, filters=None):
        """
        Search profiles based on query and filters.
        """
        from django.db.models import Q
        
        queryset = UserProfile.objects.select_related('user')
        
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(user__email__icontains=query) |
                Q(organization__icontains=query) |
                Q(job_title__icontains=query) |
                Q(icpau_registration_number__icontains=query)
            )
        
        if filters:
            if filters.get('role'):
                queryset = queryset.filter(user__role=filters['role'])
            
            if filters.get('city'):
                queryset = queryset.filter(city__icontains=filters['city'])
            
            if filters.get('organization'):
                queryset = queryset.filter(organization__icontains=filters['organization'])
            
            if filters.get('is_complete') is not None:
                queryset = queryset.filter(is_profile_complete=filters['is_complete'])
        
        return queryset.order_by('-updated_at')
