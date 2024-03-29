import requests
import random
import string
import json
import time
import io
import os
from openai import OpenAI
from flask import jsonify
from transformers import GPT2Tokenizer
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


class WebsiteComplianceChecker:
    def __init__(self, api_key, service_account_file, folder_id=None):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.service_account_file = service_account_file
        self.folder_id = folder_id
        self.file_name = ''

    def fetch_website(self, url):
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            response = requests.get(url)
            if response.status_code == 200:
                return response.text
            else:
                return f"Failed to fetch the website. Status code: {response.status_code}", 500
        except Exception as e:
            return f"An error occurred: {str(e)}", 500

    def split_website_content(self, website):
        chunks, final_part_index = [], -1
        head = website.split("</head>")[0] + "</head>"
        chunks += [head[i:i+14000] for i in range(0, len(head), 14000)] if len(head) > 14000 else [head]

        rest = website.split("</head>")[1]
        final_part_index = rest[len(rest)-14000:].find("<script>") + len(rest) - 14000 if "<script>" in rest[len(rest)-14000:] else -1
        rest, final_part = (rest[:final_part_index], rest[final_part_index:]) if final_part_index != -1 else (rest, "")

        chunks += [rest[i:i+14000] for i in range(0, len(rest), 14000)] if len(rest) > 14000 else [rest]
        if final_part:
            chunks.append(final_part)
        return chunks

    def create_message(self, message: list):
        return self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=message,
            temperature=0.5,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
    
    def chunk_analysis(self, chunk, chunk_num):
        try:
            message = [
        {
            "role": "system",
            "content": "Der Nutzer werde dir ein Stück Quellcode einer Website geben, und du musst herausfinden, ob die Website DSGVO-konform ist. Du sollst einige Notizen schreiben, die der Haupt-KI gesammelt werden können, um zu entscheiden, ob die Website DSGVO-konform ist oder nicht, denn es wird " + str(chunk_num) + " KIs geben, die verschiedene Teile der Website lesen."
        },
        {
            "role": "user",
            "content": "Hier ist dein Teil: "+ chunk
        }]
            response = self.create_message(message).choices[0].message.content.strip()
            return response
        except Exception as e:
            print(e)
            return f"An error occurred: {str(e)}", 500
        
    def join_notes(self, strings):
        joined_string = ""
        total_parts = len(strings)
        
        for index, string in enumerate(strings, start=1):
            start_marker = f"[START NOTIZE {index}/{total_parts}]"
            end_marker = f"[END NOTIZE {index}/{total_parts}]"
            joined_string += f"{start_marker}\n{string}\n{end_marker}\n"
        
        return joined_string
 
    def approximate_token_count(self, text):
        # Initialize the tokenizer
        tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
        
        # Tokenize the text and count the number of tokens
        tokens = tokenizer.encode(text, add_special_tokens=True)
        return len(tokens)

    def main_analysis(self, notes):
        try:
            str_notes = self.join_notes(notes)
            if self.approximate_token_count(str_notes) > 15000:
                return "The notes are too long"
            message = [
        {
            "role": "system",
            "content": "Du bist die Haupt-KI und musst auf Basis der gesammelten Notizen entscheiden, ob die Website DSGVO-konform ist. Deine Aufgabe ist es, eine Analyse in einem strukturierten Format zu liefern, das direkt als JSON-Objekt interpretiert werden kann. Die Analyse sollte die Einhaltung in verschiedenen Bereichen bewerten, wie Informationspflichten, Datenschutz, IT-Sicherheit und den Umgang mit Drittanbieter-Anfragen. Deine Einschätzung in jedem Bereich soll als Wert -1 für schlecht, 0 für unbekannt oder 1 für gut angegeben werden. Basierend auf den gesammelten Notizen, generiere bitte eine Ausgabe im folgenden JSON-Format (dies ist ein Beispiel für die Struktur, deine Ausgabe sollte die tatsächlichen Beobachtungen und Ratschläge widerspiegeln): { \"Informationspflichten\": { \"Impressum\": { \"Impressum vorhanden\": 1, \"Impressum aufrufbar\": 1, \"E-Mail vorhanden\": 1, \"Telefonnummer genannt\": 1, \"Vertretungsberechtigter genannt\": 1, \"Angaben zur Rechtsform vorhanden\": 1, \"Handels-/Gewerberegister genannt\": 1, \"Umsatzsteuernummer genannt\": 1 }, \"AGB\": { \"AGB vorhanden\": 1, \"AGB aufrufbar\": 1 }, \"Widerrufsbelehrung\": { \"Widerrufsbelehrung vorhanden\": 1, \"Widerrufsbelehrung aufrufbar\": 1, \"Widerrufsbelehrung genannt\": 1 } }, \"Datenschutz\": { \"Cookies\": { \"Cookies konform\": 1, \"Cookie Consent Manager vorhanden\": 1 }, \"Drittanbieter-Einbindungen\": { \"Drittanbieter in Datenschutzerklärung genannt\": 0, \"Serverstandorte konform\": 0 }, \"Datenschutzerklärung\": { \"Datenschutzerklärung vorhanden\": 1, \"Datenschutzerklärung aufrufbar\": 1 } }, \"IT-Sicherheit\": { \"Verschlüsselung\": { \"SSL-Verbindung prüfen\": 1, \"Überprüfung der Gültigkeit des Hostnames\": 1, \"Prüfung der Zertifizierungsstelle\": 1, \"Überprüfung der Gültigkeit des Zertifikats / Zertifikatskette\": 1, \"HTTPS Weiterleitung prüfen\": 1 }, \"Domain und Header\": { \"Prüfung des Hostnames\": 1, \"HSTS-Header Prüfung\": 1, \"Prüfung der X-Frame-Option\": 1, \"Landingpage aufrufbar\": 1 } }, \"Übersicht der Drittanbieter-Anfragen (3rd-Party-Requests)\": { \"Keine Einbindungen von anderen Anbietern gefunden\": 1, \"0 Dienste erheben Daten\": 1, \"Kein Dienst zugeordnet\": 1 }, \"Vorschlage\": [\"\"] }"
        },
        {
            "role": "user",
            "content": "Hier sind die Notizen: " + str_notes
        }
    ]
            response = self.create_message(message).choices[0].message.content.strip()
            return response
        except Exception as e:
            return f"An error occurred: {str(e)}", 500
        
    def parse_json(self, json_str):
        try:
            return json.loads(json_str)
        except Exception as e:
            return f"An error occurred: {str(e)}", 500
        
    def convert_json_to_html(self, json_data, url, current_time):
        json_data_str = json.dumps(json_data)
        print(json_data, url, current_time, json_data_str)
        html_content = '''<html lang="en">

    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Compliance Report with Graphs</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {
                font-family: 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                color: #333;
                background-color: #f9f9f9;
            }

            .container {
                max-width: 800px;
                margin: 40px auto;
                padding: 20px;
                background-color: #ffffff;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-radius: 8px;
            }

            h1,
            h2,
            h3 {
                color: #2c3e50;
            }

            h1 {
                font-size: 2.5em;
                margin-bottom: 30px;
            }

            h2 {
                font-size: 2em;
                margin-bottom: 20px;
            }

            h3 {
                font-size: 1.5em;
                margin-bottom: 15px;
            }

            .chart-container {
                width: 30%;
                padding: 20px;
                margin: 20px 0;
            }

            .suggestions {
                background-color: #e7f5ff;
                border-left: 6px solid #2c3e50;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                color: #333;
            }

            .good,
            .bad,
            .unknown {
                border: 2px solid #ddd;
                /* Add border to all status elements */
                padding: 10px;
                margin-bottom: 5px;
                border-radius: 4px;
            }

            .good {
                background-color: #dff0d8;
                color: #3c763d;
            }

            .unknown {
                background-color: #fcf8e3;
                color: #8a6d3b;
            }

            .bad {
                background-color: #f2dede;
                color: #a94442;
            }

            footer {
                background-color: #f4f4f4;
                color: #333;
                text-align: center;
                padding: 20px 10px;
                border-top: 1px solid #ddd;
            }

            footer a {
                color: #337ab7;
                text-decoration: none;
            }

            footer a:hover {
                text-decoration: underline;
            }
        </style>

    </head>

    <body>

        <div class="container flex flex-col font-sans max-w-4xl">
            <h1 class="text-3xl text-center font-bold">DSGVO Analyse Bericht</h1>
            <div class="flex flex-row justify-between py-[2em]">
                <div>
                    <h3>''' + url + '''</h3>
                    <span class="font-light text-xs">Analyse-Datum: '''+ current_time +''' Uhr</span>
                </div>
                <div class="text-3xl font-bold pr-[1em] text-green-400">DSGVO.AI</div>
            </div>
            <!-- Sections for Compliance Data -->
            <div class="flex flex-wrap justify-around">
                <div class="chart-container">
                    <h2 class="text-center">Informationspflichten</h2>
                    <canvas id="Informationspflichten"></canvas>
                </div>
                <div class="chart-container">
                    <h2 class="text-center">Datenschutz</h2>
                    <canvas id="Datenschutz"></canvas>
                </div>
                <div class="chart-container">
                    <h2 class="text-center">IT-Sicherheit</h2>
                    <canvas id="IT-Sicherheit"></canvas>
                </div>
            </div>
            <div class="analysis flex flex-col gap-1">
                <h1 class="text-xl text-center font-medium">Analyse-Übersicht</h1>
                <h2 class="font-medium text-xl py-[3px]">Informationspflichten</h2>
                <div class="flex flex-col gap-1 border-2 rounded-md p-[0.5em]">
                    <div class="impressum"></div>
                    <div class="agb"></div>
                    <div class="widerrufsbelehrung"></div>
                </div>
                <h2 class="font-medium text-xl py-[3px]">Datenschutz</h2>
                <div class="flex flex-col gap-1 border-2 rounded-md p-[0.5em]">
                    <div class="cookies"></div>
                    <div class="drittanbieter"></div>
                    <div class="datenschutzerklaerung"></div>
                </div>
                <h2 class="font-medium text-xl py-[3px]">IT-Sicherheit</h2>
                <div class="flex flex-col gap-1 border-2 rounded-md p-[0.5em]">
                    <div class="verschluesselung"></div>
                    <div class="domain"></div>
                </div>
            </div>


            <div class="suggestions">
                <h2 class="text-xl font-bold">Vorschläge</h2>
                <div class="border-b-2 border-black">Überprüfen Sie die fehlenden Informationen im Impressum, AGB und
                    Widerrufsbelehrung.</div>
                <div></div>
            </div>

            <footer class="text-center bg-gray-100 text-gray-600 py-4 px-6 mt-8">
                <p>&copy; 2024 DSGVO.AI. Alle Rechte vorbehalten.</p>
                <p>Die Informationen auf dieser Website dienen der allgemeinen Information und stellen keine Rechtsberatung
                    dar.</p>
                <p>Für weitere Informationen oder bei Fragen wenden Sie sich bitte an uns: <a href="mailto:info@dsgvo.ai"
                        class="text-blue-500">info@dsgvo.ai</a></p>
                <p>Diese Website nutzt Cookies, um Ihr Erlebnis zu verbessern. Mit der weiteren Nutzung dieser Website
                    stimmen Sie
                    der Verwendung von Cookies zu.</p>
            </footer>

        </div>

        <script>
            const ctx = document.getElementById('Informationspflichten').getContext('2d');
            const impressumChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['Good', 'Unknown', 'Bad'],
                    datasets: [{
                        label: 'Compliance Status',
                        data: [3, 5, 2], // Example data, replace with your actual data
                        backgroundColor: [
                            'rgba(40, 167, 69, 0.2)',
                            'rgba(255, 193, 7, 0.2)',
                            'rgba(220, 53, 69, 0.2)'
                        ],
                        borderColor: [
                            'rgba(40, 167, 69, 1)',
                            'rgba(255, 193, 7, 1)',
                            'rgba(220, 53, 69, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    legend: {
                        position: 'bottom',
                    },
                }
            });

            const ctx2 = document.getElementById('Datenschutz').getContext('2d');
            const datenschutzChart = new Chart(ctx2, {
                type: 'pie',
                data: {
                    labels: ['Good', 'Unknown', 'Bad'],
                    datasets: [{
                        label: 'Compliance Status',
                        data: [4, 4, 2], // Example data, replace with your actual data
                        backgroundColor: [
                            'rgba(40, 167, 69, 0.2)',
                            'rgba(255, 193, 7, 0.2)',
                            'rgba(220, 53, 69, 0.2)'
                        ],
                        borderColor: [
                            'rgba(40, 167, 69, 1)',
                            'rgba(255, 193, 7, 1)',
                            'rgba(220, 53, 69, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    legend: {
                        position: 'bottom',
                    },
                }
            });

            const ctx3 = document.getElementById('IT-Sicherheit').getContext('2d');
            const itSicherheitChart = new Chart(ctx3, {
                type: 'pie',
                data: {
                    labels: ['Good', 'Unknown', 'Bad'],
                    datasets: [{
                        label: 'Compliance Status',
                        data: [5, 3, 2], // Example data, replace with your actual data
                        backgroundColor: [
                            'rgba(40, 167, 69, 0.2)',
                            'rgba(255, 193, 7, 0.2)',
                            'rgba(220, 53, 69, 0.2)'
                        ],
                        borderColor: [
                            'rgba(40, 167, 69, 1)',
                            'rgba(255, 193, 7, 1)',
                            'rgba(220, 53, 69, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    legend: {
                        position: 'bottom',
                    },
                }
            });

            // Example of embedding the JSON directly. Replace this with your JSON loading method if different.
            const complianceData = ''' + json_data_str + ''';

            function calculateChartData(sectionData) {
                let good = 0, unknown = 0, bad = 0;
                Object.values(sectionData).forEach(subsection => {
                    Object.values(subsection).forEach(value => {
                        if (value === 1) good++;
                        else if (value === 0) unknown++;
                        else if (value === -1) bad++;
                    });
                });
                return [good, unknown, bad];
            }

            // Update chart data
            const infosData = calculateChartData(complianceData["Informationspflichten"]);
            impressumChart.data.datasets[0].data = infosData;
            impressumChart.update();

            const datenschutzData = calculateChartData(complianceData["Datenschutz"]);
            datenschutzChart.data.datasets[0].data = datenschutzData;
            datenschutzChart.update();

            const itSicherheitData = calculateChartData(complianceData["IT-Sicherheit"]);
            itSicherheitChart.data.datasets[0].data = itSicherheitData;
            itSicherheitChart.update();


            function createAnalysisHTML(sectionName, sectionData) {
                let htmlContent = `<h2 class="text-xl font-semibold pb-[5px]">${sectionName}</h2><div class="flex flex-col gap-1">`;

                for (const [key, value] of Object.entries(sectionData)) {
                    // Determine the icon and class based on the value
                    let icon, badgeClass;
                    switch (value) {
                        case 1:
                            icon = '✅';
                            badgeClass = 'good'; // You might need to adjust these classes based on your CSS
                            break;
                        case 0:
                            icon = '⚠️';
                            badgeClass = 'unknown';
                            break;
                        case -1:
                            icon = '⛔';
                            badgeClass = 'bad';
                            break;
                        default:
                            icon = '❓';
                            badgeClass = ''; // No specific class for undefined values
                    }

                    // Append HTML for each item
                    htmlContent += `<div class="ml-[2em] border-2 rounded-md p-[2px] pb-[3px] ${badgeClass}">${icon} ${key}</div>`;
                }

                htmlContent += '</div>';
                return htmlContent;
            }

            // Generate HTML for Informationspflichten
            const informPflichtenHTML = createAnalysisHTML('Impressum', complianceData['Informationspflichten']['Impressum']);
            // Assuming there's a div with class="analysis" in your HTML
            document.querySelector('.impressum').innerHTML = informPflichtenHTML;
            document.querySelector('.agb').innerHTML = createAnalysisHTML('AGB', complianceData['Informationspflichten']['AGB']);
            document.querySelector('.widerrufsbelehrung').innerHTML = createAnalysisHTML('Widerrufsbelehrung', complianceData['Informationspflichten']['Widerrufsbelehrung']);
            document.querySelector('.cookies').innerHTML = createAnalysisHTML('Cookies', complianceData['Datenschutz']['Cookies']);
            document.querySelector('.drittanbieter').innerHTML = createAnalysisHTML('Drittanbieter-Einbindungen', complianceData['Datenschutz']['Drittanbieter-Einbindungen']);
            document.querySelector('.datenschutzerklaerung').innerHTML = createAnalysisHTML('Datenschutzerklärung', complianceData['Datenschutz']['Datenschutzerklärung']);
            document.querySelector('.verschluesselung').innerHTML = createAnalysisHTML('Verschlüsselung', complianceData['IT-Sicherheit']['Verschlüsselung']);
            document.querySelector('.domain').innerHTML = createAnalysisHTML('Domain und Header', complianceData['IT-Sicherheit']['Domain und Header']);


            function findSuggestions(obj, key1, key2) {
                // Check for the first key
                if (obj.hasOwnProperty(key1)) {
                    return obj[key1];
                }
                // Check for the second key
                if (obj.hasOwnProperty(key2)) {
                    return obj[key2];
                }
                // Recursively search in child objects
                for (let prop in obj) {
                    if (typeof obj[prop] === 'object') {
                    let found = findSuggestions(obj[prop], key1, key2);
                    if (found) {
                        return found;
                    }
                    }
                }
                return null; // Key not found
            }

            // Use the function to search for "Vorschläge" or "Vorschlage" in 'complianceData'
            const suggestions = findSuggestions(complianceData, "Vorschläge", "Vorschlage");
            if (suggestions) {
                const suggestionsContainer = document.querySelector('.suggestions');
                suggestionsContainer.innerHTML = '<h2 class="text-xl font-bold">Vorschläge</h2>' + suggestions.map(suggestion => `<div>- ${suggestion}</div>`).join('');
            } else {
                console.log('No suggestions key found');
            }


        </script>

    </body>

    </html>'''
        return html_content     

    def save_html(self, html_content):
        self.file_name = '/tmp/' + ''.join(random.choice(string.ascii_lowercase) for i in range(10)) + '.html'
        print(self.file_name)
        with open(self.file_name, 'w') as file:
            file.write(html_content)
        return self.file_name

    def upload_to_google_drive(self, mimetype='text/html', description=''):
        credentials = Credentials.from_service_account_file(self.service_account_file, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=credentials)

        file_metadata = {'name': self.file_name, 'mimeType': mimetype, 'description': description}
        if self.folder_id:
            file_metadata['parents'] = [self.folder_id]

        media = MediaIoBaseUpload(io.BytesIO(open(self.file_name, 'rb').read()), mimetype=mimetype)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')

    def process_website(self, url, email):
        website_content = self.fetch_website(url)
        if isinstance(website_content, tuple):
            return website_content  # Error case
        print(website_content)

        chunks = self.split_website_content(website_content)
        print(len(chunks))
        print(chunks)
        notes = [self.chunk_analysis(chunk, len(chunks)) for chunk in chunks]
        print(notes)
        analysis = self.main_analysis(notes)
        print(analysis)

        analysis_json = self.parse_json(analysis)
        print(analysis_json)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(current_time)
        html_content = self.convert_json_to_html(analysis_json, url, current_time)
        print(html_content)
        self.save_html(html_content)

        uploaded_file_id = self.upload_to_google_drive('text/html', email)
        return uploaded_file_id

def analyse_website(request):
    # Preflight request handling
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {
        'Access-Control-Allow-Origin': '*'
    }
    
    api_key = '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'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    service_account_file = os.path.join(current_dir, 'hear2act-b7aab2b14187.json')
    folder_id = '1qSJpXUR3u6y4jcFlTZeURY0G2Z_0x8yG'

    checker = WebsiteComplianceChecker(api_key=api_key, service_account_file=service_account_file, folder_id=folder_id)

    request_json = request.get_json(silent=True)
    if request_json and 'url' in request_json and 'email' in request_json:
        url = request_json['url']
        email = request_json['email']
    else:
        return jsonify({"error": "No URL or email provided"}), 400, headers

    try:
        analysis_result_id = checker.process_website(url, email)
        response_data = {
            "message": f"Website compliance analysis completed successfully with file ID: {analysis_result_id} and file name: {checker.file_name}",
            "file_id": analysis_result_id,
            "file_name": checker.file_name,
            "status": "success",
            "website": url
        }
        return jsonify(response_data), 200, headers
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}", "status": "error"}), 200, headers