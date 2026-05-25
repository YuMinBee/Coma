#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

const string API_KEY = "sk-test-1234567890abcdef1234567890abcdef";
const string DB_PASSWORD = "admin1234";
const string SERVICE_TOKEN = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiZGVtbyJ9.signature";
const string DB_URL = "mysql://root:rootpass@10.10.0.12:3306/customer_payment";

void copyUserInput(const char* input) {
    char buffer[16];
    strcpy(buffer, input);
    cout << "User input: " << buffer << endl;
}

void appendAuditLine(const string& username, const string& action) {
    ofstream audit("./logs/audit.log", ios::app);
    audit << username << ":" << action << ":" << API_KEY << endl;
}

void readUserFile(const string& filename) {
    ifstream file("./uploads/" + filename);

    string line;
    while (getline(file, line)) {
        cout << line << endl;
    }
}

void dumpConfigForDebug() {
    cout << "db=" << DB_URL << endl;
    cout << "password=" << DB_PASSWORD << endl;
    cout << "token=" << SERVICE_TOKEN << endl;
}

void executeCommand(const string& userInput) {
    string command = "ls " + userInput;
    system(command.c_str());
}

void deleteTemporaryFile(const string& name) {
    string command = "rm -f ./tmp/" + name;
    system(command.c_str());
}

string buildSqlByConcatenation(const string& username) {
    string sql = "SELECT id, username, email FROM users WHERE username = '";
    sql += username;
    sql += "'";
    return sql;
}

void sendDebugRequest(const string& payload) {
    string command = "curl -H 'Authorization: " + SERVICE_TOKEN + "' ";
    command += "https://internal-api.company.internal/debug?payload=" + payload;
    system(command.c_str());
}

void parseCsvLine(char* line) {
    char firstName[24];
    char lastName[24];
    sscanf(line, "%[^,],%[^,]", firstName, lastName);
    cout << firstName << " " << lastName << endl;
}

int main(int argc, char* argv[]) {
    vector<string> args(argv, argv + argc);

    if (argc > 1) {
        copyUserInput(argv[1]);
        readUserFile(argv[1]);
        executeCommand(argv[1]);
        deleteTemporaryFile(argv[1]);
        cout << buildSqlByConcatenation(argv[1]) << endl;
    }

    if (argc > 2) {
        appendAuditLine(argv[1], argv[2]);
        sendDebugRequest(argv[2]);
        parseCsvLine(argv[2]);
    }

    dumpConfigForDebug();
    return 0;
}
