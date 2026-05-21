# This file is part of CAT-SOOP
# Copyright (c) 2011-2023 by The CAT-SOOP Developers <catsoop-dev@mit.edu>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

cs_auth_required = False
cs_course_available = False
cs_breadcrumbs_skip = True

# import sqlite3
# import os

# def cs_preload(context):
#     # Database will be created in your course's data directory
#     db_path = os.path.join(context['cs_data_root'], 'quiz_database.db')
    
#     try:
#         # Connect to SQLite database (creates if doesn't exist)
#         conn = sqlite3.connect(db_path)
#         cursor = conn.cursor()
        
#         # Create tables for your quiz system
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS questions (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 question_text TEXT NOT NULL,
#                 question_type TEXT NOT NULL,
#                 options TEXT,  # JSON string of options
#                 correct_answers TEXT  # JSON string of correct answers
#             )
#         ''')
        
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS quiz_attempts (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 username TEXT NOT NULL,
#                 score INTEGER NOT NULL,
#                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
#                 details TEXT  # JSON string of attempt details
#             )
#         ''')
        
#         # Save changes
#         conn.commit()
        
#         # Make database connection available to handlers
#         context['cs_quiz_db'] = {
#             'conn': conn,
#             'cursor': cursor,
#             'path': db_path
#         }
        
#     except Exception as e:
#         print(f"Database error: {str(e)}")
#         context['cs_quiz_error'] = str(e)