from flask import Flask
from perf.perfreport import perf_compare,perf_compare_ui,importperfresult,upload_file,perf_compare_json_report

app = Flask(__name__,template_folder='.//perf//templates')

@app.route("/perfcompare/<baseline_release>/<current_release>")
def perfcompare(baseline_release, current_release):
    '''
	This service takes baseline_release and current_release as parameters and  renders html page which displays comparison based on parameters passed.
    :param baseline_release:
    :param current_release:
    :return:
    '''
    return perf_compare(baseline_release, current_release)

@app.route("/perfcompareui", methods=['POST', 'GET'])
def perfcompareui():
    '''
    This service is used to display available releases for performance comparsion.
    '''
    return perf_compare_ui()

@app.route("/uploadcsv")
def import_perf_result() :
    '''
    This service is used to upload csv file data to mongo db
    :return:
    '''

    return importperfresult()

@app.route('/importPerfResult', methods = ['POST'])
def uploadfile() :
    '''
    This api renders html form to upload csv
    :return:
    '''
    return upload_file()

@app.route("/perfcompare/result/json", methods=['POST'])
def perfcomparejsonreport() :
    return perf_compare_json_report()

if __name__ == "__main__":
    app.run("0.0.0.0", 5002, debug=True)